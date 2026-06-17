#!/usr/bin/env python3
"""Join a LiveKit room to interact with the voice agent with microphone input.

- Choppy/interrupted agent voice (QueueFull): we increase the AudioMixer buffer below.
  Also try: close other apps, wired connection, more CPU for the voice worker.
- Slow replies / "inference slower than realtime": on the worker machine set
  VOICE_USE_WEBRTC_VAD=1 to use WebRTC VAD instead of Silero (lower latency, slightly
  less accurate turn detection).
- Hearing the same reply twice: (1) Client keeps only one agent track in the player.
  (2) Per LiveKit docs, mute your mic while the agent is speaking to prevent echo
  (agent TTS → your speakers → your mic → STT → agent "hears" itself and replies again).
  Set VOICE_CLIENT_MUTE_WHILE_AGENT_SPEAKING=1 to auto-mute mic while agent speaks.
  Unmute is reliable: when the agent track ends (track_unsubscribed), after sustained
  silence on the agent stream, or after VOICE_CLIENT_MUTE_DURATION_SEC (max fallback).
"""

import asyncio
import os
import sys
from pathlib import Path

# Increase LiveKit AudioMixer output queue to reduce QueueFull / choppy playback
# when the agent sends long TTS bursts (default capacity=100 can fill up).
try:
    import livekit.rtc.audio_mixer as _am

    _orig_am_init = _am.AudioMixer.__init__

    def _mixer_init(self, sample_rate, num_channels, *, blocksize=0, stream_timeout_ms=100, capacity=400):
        _orig_am_init(
            self, sample_rate, num_channels, blocksize=blocksize, stream_timeout_ms=stream_timeout_ms, capacity=capacity
        )

    _am.AudioMixer.__init__ = _mixer_init
except Exception:
    pass

# Avoid Windows console UnicodeEncodeError (cp1252) in some environments.
try:
    if hasattr(sys.stdout, "reconfigure"):
        sys.stdout.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
    if hasattr(sys.stderr, "reconfigure"):
        sys.stderr.reconfigure(encoding="utf-8", errors="replace", line_buffering=True)
except Exception:
    pass

# Load .env from project root (parent of scripts/)
try:
    from dotenv import load_dotenv

    _root = Path(__file__).resolve().parent.parent
    load_dotenv(_root / ".env", override=False)
except Exception:
    pass

from livekit import api, rtc

# Check for sounddevice (required for microphone capture)
import importlib.util

SOUNDDEVICE_AVAILABLE = importlib.util.find_spec("sounddevice") is not None
if not SOUNDDEVICE_AVAILABLE:
    print("WARNING: sounddevice not installed. Install it with: pip install sounddevice")
    print("Microphone capture will not work without it.")


async def main() -> None:
    room_name = (sys.argv[1] if len(sys.argv) > 1 else "my-voice-room").strip()
    if not room_name:
        room_name = "my-voice-room"

    url = os.getenv("LIVEKIT_URL")
    api_key = os.getenv("LIVEKIT_API_KEY")
    api_secret = os.getenv("LIVEKIT_API_SECRET")

    if not all([url, api_key, api_secret]):
        print("ERROR: Missing LIVEKIT_URL, LIVEKIT_API_KEY, or LIVEKIT_API_SECRET in .env")
        sys.exit(1)

    if not SOUNDDEVICE_AVAILABLE:
        print("\nERROR: sounddevice is required for microphone capture.")
        print("Install it with: pip install sounddevice")
        sys.exit(1)

    # Create access token for this participant
    token = (
        api.AccessToken(api_key, api_secret)
        .with_identity("user-test")
        .with_grants(
            api.VideoGrants(
                room_join=True,
                room=room_name,
                can_publish=True,
                can_subscribe=True,
            )
        )
        .to_jwt()
    )

    # Explicit dispatch of the voice agent to this room (LiveKit AgentDispatch API).
    # NOTE:
    # - LiveKit Cloud + RoomConfiguration can already auto-dispatch the agent.
    # - Doing *both* (auto-dispatch + this block) creates multiple agents per room.
    # Default behavior now is to SKIP explicit dispatch unless LIVEKIT_EXPLICIT_DISPATCH=1.
    explicit_dispatch = os.getenv("LIVEKIT_EXPLICIT_DISPATCH", "").strip() == "1"
    if explicit_dispatch:
        try:
            print(f"\nDispatching agent 'narrative-voice' to room '{room_name}'...")
            lkapi = api.LiveKitAPI(url, api_key, api_secret)
            try:
                await asyncio.wait_for(
                    lkapi.agent_dispatch.create_dispatch(
                        api.CreateAgentDispatchRequest(
                            agent_name="narrative-voice",
                            room=room_name,
                            metadata="",
                        )
                    ),
                    timeout=8.0,
                )
                print(f"[OK] Dispatched agent 'narrative-voice' to room '{room_name}'.")
            except asyncio.TimeoutError:
                print("[WARN] Dispatch request timed out; continuing to connect anyway.")
            finally:
                await lkapi.aclose()
        except Exception as e:
            print(f"\n[WARN] Could not explicitly dispatch agent: {e}")
    else:
        print(
            "\n[INFO] Skipping explicit agent dispatch (LIVEKIT_EXPLICIT_DISPATCH!=1). "
            "Relying on LiveKit RoomConfiguration/Cloud to dispatch 'narrative-voice'."
        )

    print(f"\nConnecting to room: {room_name}")
    print(f"URL: {url}")

    # Create room and connect
    room = rtc.Room()
    mic_capture = None
    audio_track = None  # LocalAudioTrack we publish; used to mute/unmute while agent speaks (echo fix)
    output_player = None  # plays agent's audio to speakers (created after open_input for AEC)
    output_player_started = False
    pending_agent_audio_tracks = []  # agent tracks that arrived before output_player was ready
    agent_audio_track_sids = set()  # avoid playing the same agent track twice (e.g. duplicate events)
    agent_tracks_added_to_player = set()  # sids of tracks already added to output_player (prevent double add)
    current_agent_track = None  # only one agent track in player at a time (avoids double playback on republish)
    unmute_mic_task = None  # max-duration fallback: unmute after mute_duration_sec
    silence_unmute_task = None  # optional: unmute when agent audio is silent for silence_unmute_ms
    mute_while_agent_speaks = os.getenv("VOICE_CLIENT_MUTE_WHILE_AGENT_SPEAKING", "").strip().lower() in (
        "1",
        "true",
        "yes",
    )
    mute_duration_sec = float(os.getenv("VOICE_CLIENT_MUTE_DURATION_SEC", "3"))
    silence_unmute_ms = int(os.getenv("VOICE_CLIENT_SILENCE_UNMUTE_MS", "500"))
    shutdown = asyncio.Event()

    def _do_unmute_mic() -> None:
        """Unmute mic and cancel any scheduled unmute tasks (echo-fix)."""
        nonlocal unmute_mic_task, silence_unmute_task
        for t in (unmute_mic_task, silence_unmute_task):
            if t is not None and not t.done():
                t.cancel()
        unmute_mic_task = None
        silence_unmute_task = None
        if audio_track is not None:
            try:
                audio_track.unmute()
            except Exception:
                pass

    def _is_silence(frame: rtc.AudioFrame, threshold: int = 512) -> bool:
        """True if frame is effectively silence (max 16-bit amplitude below threshold)."""
        try:
            data = frame.data
            if data is None or len(data) == 0:
                return True
            # data is memoryview of int16
            return max(abs(int(x)) for x in data) < threshold
        except Exception:
            return True

    @room.on("participant_connected")
    def on_participant_connected(participant: rtc.RemoteParticipant):
        print(f"\n✓ Participant connected: {participant.identity} (sid={participant.sid})")
        if participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            print("  → This is the voice agent!")

    @room.on("track_subscribed")
    def on_track_subscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        nonlocal output_player_started, current_agent_track, unmute_mic_task, silence_unmute_task
        print(f"\n✓ Subscribed to track: {track.kind} from {participant.identity}")
        if track.kind == rtc.TrackKind.KIND_AUDIO and participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            track_sid = getattr(track, "sid", None) or getattr(publication, "sid", id(track))
            if track_sid in agent_audio_track_sids:
                print("  → Agent audio track already playing (skipping duplicate)")
                return
            agent_audio_track_sids.add(track_sid)
            if track_sid in agent_tracks_added_to_player:
                print("  → Agent track already added to player (skipping)")
                return
            # Reserve immediately so a second event can't add the same track
            agent_tracks_added_to_player.add(track_sid)
            print("  → Audio track ready - you should hear the agent's voice")
            if output_player is not None:

                async def add_and_play_agent_track():
                    nonlocal output_player_started, current_agent_track, unmute_mic_task, silence_unmute_task
                    try:
                        # Only one agent track at a time: remove previous so we never hear the same reply twice
                        if current_agent_track is not None:
                            try:
                                await output_player.remove_track(current_agent_track)
                            except Exception:
                                pass
                            prev_sid = getattr(current_agent_track, "sid", None)
                            if prev_sid is not None:
                                agent_tracks_added_to_player.discard(prev_sid)
                            current_agent_track = None
                        await output_player.add_track(track)
                        current_agent_track = track
                        if not output_player_started:
                            await output_player.start()
                            output_player_started = True
                        print("  → Agent audio playing to your speakers")
                        # Mute mic while agent speaks to prevent echo; unmute when track ends, after silence, or after max duration
                        if mute_while_agent_speaks and audio_track is not None:
                            _do_unmute_mic()  # cancel any previous unmute tasks
                            try:
                                audio_track.mute()
                            except Exception:
                                pass

                            # Max-duration fallback (so you're never stuck muted for 10s)
                            async def unmute_after_max():
                                await asyncio.sleep(mute_duration_sec)
                                _do_unmute_mic()

                            unmute_mic_task = asyncio.create_task(unmute_after_max())

                            # Optional: unmute as soon as agent audio is silent for silence_unmute_ms
                            async def unmute_on_silence():
                                nonlocal silence_unmute_task
                                try:
                                    stream = rtc.AudioStream.from_track(
                                        track=track,
                                        sample_rate=output_player._sample_rate if output_player else 48000,
                                        num_channels=output_player._num_channels if output_player else 1,
                                    )
                                    try:
                                        silence_frames_needed = max(1, silence_unmute_ms // 20)  # ~20 ms per frame
                                        silence_count = 0
                                        async for ev in stream:
                                            if _is_silence(ev.frame):
                                                silence_count += 1
                                                if silence_count >= silence_frames_needed:
                                                    _do_unmute_mic()
                                                    return
                                            else:
                                                silence_count = 0
                                        # Stream ended (EOS) -> unmute
                                        _do_unmute_mic()
                                    finally:
                                        try:
                                            await stream.aclose()
                                        except Exception:
                                            pass
                                except Exception:
                                    pass  # fall back to max-duration unmute

                            try:
                                silence_unmute_task = asyncio.create_task(unmute_on_silence())
                            except Exception:
                                pass
                    except Exception as e:
                        agent_tracks_added_to_player.discard(track_sid)
                        print(f"  [ERROR] Failed to play agent audio: {e}")

                asyncio.create_task(add_and_play_agent_track())
            else:
                agent_tracks_added_to_player.discard(track_sid)  # will add when player is ready
                pending_agent_audio_tracks.append((track, track_sid))
                print("  → Will play agent audio when speaker is ready")
        if hasattr(publication, "metadata") and publication.metadata and isinstance(publication.metadata, dict):
            em = publication.metadata.get("emotion")
            if em:
                print(f"  → Emotion: {em}")

    @room.on("track_unsubscribed")
    def on_track_unsubscribed(track: rtc.Track, publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        nonlocal current_agent_track
        if track.kind == rtc.TrackKind.KIND_AUDIO and participant.kind == rtc.ParticipantKind.PARTICIPANT_KIND_AGENT:
            track_sid = getattr(track, "sid", None) or getattr(publication, "sid", None)

            async def remove_agent_track():
                nonlocal current_agent_track
                if output_player is not None:
                    try:
                        await output_player.remove_track(track)
                    except Exception:
                        pass
                if current_agent_track is track or (
                    track_sid and getattr(current_agent_track, "sid", None) == track_sid
                ):
                    current_agent_track = None
                    # Unmute as soon as agent track ends (reliable; no fixed 10s wait)
                    _do_unmute_mic()
                if track_sid is not None:
                    agent_tracks_added_to_player.discard(track_sid)
                    agent_audio_track_sids.discard(track_sid)

            asyncio.create_task(remove_agent_track())

    @room.on("track_published")
    def on_track_published(publication: rtc.TrackPublication, participant: rtc.RemoteParticipant):
        print(f"\n✓ Track published: {publication.kind} from {participant.identity}")
        if participant.identity == room.local_participant.identity:
            print("  → Your microphone is now active!")

    @room.on("disconnected")
    def on_disconnected():
        print("\n[DISCONNECTED] Disconnected from room")
        shutdown.set()

    @room.on("connected")
    def on_connected():
        print("\n✓ Connected to room!")
        print("  → The voice agent should join automatically")
        # Microphone and speaker are set up in setup_microphone_after_connect() only
        # (single setup to avoid duplicate tracks and duplicate playback)

    @room.on("connection_state_changed")
    def on_connection_state_changed(state: rtc.ConnectionState):
        print(f"\n🔌 Connection state: {state}")
        if state == rtc.ConnectionState.CONN_CONNECTED:
            print("  → Successfully connected!")
        elif state == rtc.ConnectionState.CONN_DISCONNECTED:
            print("  → Disconnected")
        elif state == rtc.ConnectionState.CONN_RECONNECTING:
            print("  → Reconnecting...")
        else:
            print(f"  → State: {state}")

    # Set up microphone AFTER connection (not in callback, to ensure it runs)
    async def setup_microphone_after_connect():
        nonlocal mic_capture, audio_track, output_player, output_player_started, current_agent_track
        # Wait a bit for connection to fully establish
        await asyncio.sleep(0.5)

        try:
            print("\nSetting up microphone...")
            devices = rtc.MediaDevices()

            # List available input devices
            input_devices = devices.list_input_devices()
            if input_devices:
                print("\nAvailable microphones:")
                default_idx = devices.default_input_device()
                for dev in input_devices:
                    marker = " ← DEFAULT" if dev["index"] == default_idx else ""
                    print(f"  [{dev['index']}] {dev['name']}{marker}")
            else:
                print("  [WARN] No input devices found!")

            # Open microphone input
            print("\nOpening microphone...")
            mic_capture = devices.open_input(
                enable_aec=True,
                noise_suppression=True,
                auto_gain_control=True,
            )
            print("  ✓ Microphone opened")

            # Open speaker output right after input (so we can play agent audio; AEC uses same APM)
            print("  Opening speaker output for agent audio...")
            output_player = devices.open_output()
            print("  ✓ Speaker output ready")

            # Play any agent tracks that already arrived before we had output_player (only one at a time)
            if pending_agent_audio_tracks:
                for item in pending_agent_audio_tracks:
                    track = item[0] if isinstance(item, tuple) else item
                    track_sid = item[1] if isinstance(item, tuple) else (getattr(track, "sid", None) or id(track))
                    if track_sid in agent_tracks_added_to_player:
                        continue
                    try:
                        if current_agent_track is not None:
                            try:
                                await output_player.remove_track(current_agent_track)
                            except Exception:
                                pass
                            prev_sid = getattr(current_agent_track, "sid", None)
                            if prev_sid is not None:
                                agent_tracks_added_to_player.discard(prev_sid)
                            current_agent_track = None
                        await output_player.add_track(track)
                        current_agent_track = track
                        agent_tracks_added_to_player.add(track_sid)
                        # (Mute-while-agent-speaks not done here: audio_track is created after this block.)
                    except Exception as e:
                        print(f"  [WARN] Could not add queued agent track: {e}")
                if not output_player_started:
                    await output_player.start()
                    output_player_started = True
                    print("  → Agent audio now playing to your speakers")
                pending_agent_audio_tracks.clear()

            # Create audio track from the microphone source
            print("  Creating audio track...")
            audio_track = rtc.LocalAudioTrack.create_audio_track("microphone", mic_capture.source)
            print("  ✓ Audio track created")

            # Publish the audio track
            print("  Publishing audio track...")
            options = rtc.TrackPublishOptions(source=rtc.TrackSource.SOURCE_MICROPHONE)
            publication = await room.local_participant.publish_track(audio_track, options)
            print(f"  ✓ Track published (sid={publication.sid})")

            print("\n[OK] Microphone active! Speak into your microphone.")
            print("  → Wait for the agent's greeting to finish, then speak clearly.")
            print("  → Pause briefly when you finish so the agent can respond.\n")

        except Exception as e:
            import traceback

            print(f"\n[ERROR] Error setting up microphone: {e}")
            print(f"  Traceback: {traceback.format_exc()}")
            print("  → You can still listen to the agent, but won't be able to speak")

    try:
        print("\nConnecting...")
        try:
            # Add timeout to connection
            await asyncio.wait_for(room.connect(url, token), timeout=10.0)
        except asyncio.TimeoutError:
            print("\n[ERROR] Connection timeout! Check your network and LiveKit URL.")
            sys.exit(1)
        except Exception as e:
            print(f"\n[ERROR] Connection failed: {e}")
            import traceback

            traceback.print_exc()
            sys.exit(1)

        print("\n✓ Connection established!")
        print("Waiting for events... (Press Ctrl+C to exit)")

        # Check if we're actually connected
        if room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
            print(f"  Room: {room.name}")
            print(f"  Local participant: {room.local_participant.identity}")
            print(f"  Remote participants: {len(room.remote_participants)}")
            if len(room.remote_participants) == 0:
                print("  → Waiting for agent to join...")
        else:
            print(f"  [WARN] Connection state is {room.connection_state}")

        # Set up microphone (run after connection); keep reference so we can cancel on exit
        mic_setup_task = asyncio.create_task(setup_microphone_after_connect())

        # Periodic "still waiting" so it's clear the app is alive, not stuck in a loop
        async def periodic_status():
            while room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                await asyncio.sleep(15)
                if room.connection_state != rtc.ConnectionState.CONN_CONNECTED:
                    break
                if len(room.remote_participants) > 0:
                    break  # agent joined, stop reminding
                print("  Still waiting for agent... (Press Ctrl+C to exit)")

        # Optional timeout: exit if agent never joins (env AGENT_JOIN_TIMEOUT_SEC, 0 = wait forever)
        timeout_sec = int(os.getenv("AGENT_JOIN_TIMEOUT_SEC", "300"))

        async def timeout_if_no_agent():
            if timeout_sec <= 0:
                await shutdown.wait()
                return
            await asyncio.sleep(timeout_sec)
            if not shutdown.is_set() and len(room.remote_participants) == 0:
                print(
                    "\n[WARN] Agent did not join in time. Make sure the voice worker is running with agent_name='narrative-voice'."
                )
                shutdown.set()

        status_task = asyncio.create_task(periodic_status())
        timeout_task = asyncio.create_task(timeout_if_no_agent())
        try:
            # Keep the connection alive until Ctrl+C, disconnect, or timeout
            await shutdown.wait()
        except asyncio.CancelledError:
            # Ctrl+C or task cancel: disconnect gracefully before loop closes
            print("\n\nDisconnecting...")
        finally:
            shutdown.set()  # allow timeout task to exit if it was waiting
            mic_setup_task.cancel()
            try:
                await mic_setup_task
            except asyncio.CancelledError:
                pass
            except Exception:
                pass
            status_task.cancel()
            timeout_task.cancel()
            for t in (status_task, timeout_task):
                try:
                    await t
                except asyncio.CancelledError:
                    pass
            # Always disconnect and close mic + output player so LiveKit cleans up before event loop closes
            _do_unmute_mic()
            try:
                if output_player:
                    await asyncio.wait_for(output_player.aclose(), timeout=1.0)
            except Exception:
                pass
            try:
                if mic_capture:
                    await asyncio.wait_for(mic_capture.aclose(), timeout=1.0)
            except Exception:
                pass
            try:
                if room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                    await asyncio.wait_for(room.disconnect(), timeout=2.0)
            except Exception:
                pass
            await asyncio.sleep(0.25)  # let LiveKit finish cleanup and avoid "Event loop is closed"
    except KeyboardInterrupt:
        print("\n\nDisconnecting...")
        try:
            if output_player:
                await asyncio.wait_for(output_player.aclose(), timeout=1.0)
            if mic_capture:
                await asyncio.wait_for(mic_capture.aclose(), timeout=1.0)
            if room.connection_state == rtc.ConnectionState.CONN_CONNECTED:
                await asyncio.wait_for(room.disconnect(), timeout=2.0)
            await asyncio.sleep(0.25)
        except Exception:
            pass
    except Exception as e:
        print(f"\n[ERROR] {e}")
        try:
            if output_player:
                await output_player.aclose()
            if mic_capture:
                await mic_capture.aclose()
            await room.disconnect()
        except Exception:
            pass
        sys.exit(1)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        pass  # already handled in main
