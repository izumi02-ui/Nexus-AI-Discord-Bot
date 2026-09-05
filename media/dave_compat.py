"""Compatibility layer for inbound Discord DAVE voice frames.

Discord requires DAVE/E2EE for voice calls.  discord.py 2.7 maintains the
cryptographic session, but discord-ext-voice-recv 0.5.2a179 decodes the Opus
payload before applying that session.  Until the upstream receive extension
ships its DAVE patch, Nexus applies the same guarded ordering locally.

The patch is deliberately version-shaped and idempotent: if upstream exposes
its own ``_dave_decrypt`` implementation, Nexus leaves it alone.
"""

from __future__ import annotations

from dataclasses import dataclass

from utils.logger import logger


@dataclass(frozen=True, slots=True)
class DaveCompatibility:
    ready: bool
    patched: bool
    detail: str


def install_voice_receive_dave_patch() -> DaveCompatibility:
    """Install inbound DAVE decryption for the pinned voice-recv release."""
    try:
        import davey
        from discord.opus import OpusError
        from discord.ext.voice_recv.opus import PacketDecoder, VoiceData
    except Exception as error:  # noqa: BLE001 - reported through /voice status
        return DaveCompatibility(False, False, f"DAVE dependencies unavailable: {error}")

    if hasattr(PacketDecoder, "_dave_decrypt"):
        return DaveCompatibility(True, False, "voice-recv provides native DAVE receive")

    if getattr(PacketDecoder, "_nexus_dave_compatible", False):
        return DaveCompatibility(True, True, "Nexus DAVE compatibility active")

    required = (
        "_decode_packet",
        "_get_cached_member",
        "sink",
    )
    if any(not hasattr(PacketDecoder, name) for name in required):
        return DaveCompatibility(
            False,
            False,
            "voice-recv internals changed; update the Nexus DAVE compatibility layer",
        )

    def decrypt_in_place(decoder, packet) -> None:
        if not packet or not getattr(packet, "decrypted_data", None):
            return

        voice_client = decoder.sink.voice_client
        state = getattr(voice_client, "_connection", None)
        session = getattr(state, "dave_session", None)
        if (
            session is None
            or not getattr(session, "ready", False)
            or getattr(state, "dave_protocol_version", 0) == 0
        ):
            return

        user_id = decoder._cached_id
        if user_id is None:
            return

        try:
            packet.decrypted_data = session.decrypt(
                int(user_id),
                davey.MediaType.audio,
                bytes(packet.decrypted_data),
            )
        except Exception as error:  # unencrypted silence/keepalive can land here
            logger.debug("DAVE passthrough for SSRC %s: %s", decoder.ssrc, error)

    def process_packet(decoder, packet):
        pcm = None
        member = decoder._get_cached_member()

        if member is None:
            decoder._cached_id = decoder.sink.voice_client._get_id_from_ssrc(
                decoder.ssrc
            )
            member = decoder._get_cached_member()

        decrypt_in_place(decoder, packet)

        if not decoder.sink.wants_opus():
            try:
                packet, pcm = decoder._decode_packet(packet)
            except OpusError as error:
                # A single malformed frame must not kill the receive thread.
                logger.debug("Dropped undecodable voice frame for SSRC %s: %s", decoder.ssrc, error)
                pcm = b""

        data = VoiceData(packet, member, pcm=pcm)
        decoder._last_seq = packet.sequence
        decoder._last_ts = packet.timestamp
        return data

    PacketDecoder._process_packet = process_packet
    PacketDecoder._nexus_dave_compatible = True
    PacketDecoder._nexus_dave_decrypt = decrypt_in_place

    logger.info("Nexus inbound DAVE voice compatibility enabled.")
    return DaveCompatibility(True, True, "Nexus DAVE compatibility active")
