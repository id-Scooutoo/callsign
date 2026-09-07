# voiceprint/

Everything the bot needs to speak in a particular voice lives here, and none of
it is committed — `.gitignore` keeps the audio, the clips and `latents.pt` out
of the repository. A fresh clone starts with an empty voice.

## Making one

1. **Read [`../VOICE-CONSENT.md`](../VOICE-CONSENT.md) first** if the voice is
   not your own.

2. Put a recording at `voiceprint/source.mp3`.

   | | |
   |---|---|
   | Length | 5–20 minutes of continuous speech. More is better; the script picks 15 representative clips across the whole recording so the timbre generalises. |
   | Content | Normal conversational speech in the language the bot will speak. Reading aloud works, but sounds flatter than talking. |
   | Quality | One speaker, no music, no other voices, no heavy compression. A phone in a quiet room beats a good mic in a noisy one. |

3. Build the voiceprint:

   ```bash
   python scripts/make_voiceprint.py
   ```

   It converts and segments the source on silence, builds normalized XTTS-v2
   speaker latents, measures the speaker's real median F0, then pitch-matches
   the synthesized clone to it with the WORLD vocoder — a formant-preserving
   shift, so the result lands lower and stays natural instead of sounding
   phase-shifted.

4. Listen to what it produced:

   - `sample_clone.wav` — raw XTTS output
   - `sample_clone_matched.wav` — after pitch matching (this is what the bot sounds like)

   Not close enough? Tune and re-run:

   | Variable | Default | Effect |
   |---|---|---|
   | `CS_TEMP` | `0.55` | Sampling temperature. Lower is steadier, higher is more expressive. |
   | `CS_CLIPS` | `15` | How many reference clips feed the latents. More clips generalise better, up to a point. |
   | `CS_FACTOR` | auto | Override the measured pitch factor when the automatic one overshoots. |

## What ends up here

| File | |
|---|---|
| `source.mp3` | your recording (input) |
| `full.wav` | the converted source |
| `clips/` | the segments chosen for the latents |
| `latents.pt` | the speaker embedding the bot loads at runtime |
| `pitch_factor.txt` | the measured F0 correction |
| `sample_*.wav` | listening tests |

To remove a voice, delete this directory's contents and set `VOICE_ENABLED=false`.
The bot keeps working in text mode.
