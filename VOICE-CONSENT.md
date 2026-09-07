# Consent for a cloned voice

This project clones a voice from a recording. If the voice is not yours, get
permission first, in writing, before you build a voiceprint from it.

That is not legal boilerplate. A cloned voice is biometric data about a real
person, it is convincing enough to be misused, and the person it belongs to is
the only one who can agree to it. In the EU, voice used to identify someone
falls under GDPR, and the EU AI Act requires that synthetic audio be disclosed
as synthetic. Several US states treat voice as a protected likeness.

## Before you record

Ask, and write down what was agreed. This template is a starting point — keep
the copy that matches what you actually agreed.

```
# Voice cloning consent

<Name> has agreed to have their voice cloned from <what recordings>, for use
in <exactly which project, running where>.

Agreed on: <date>.

Scope:
- <where the synthesized audio may be played, and where it may not>
- <whether the voice model, latents and reference audio may leave your machine>
- <whether new recordings may be made without asking again>

Withdrawal: if <Name> withdraws consent, <what happens> — deleting
voiceprint/ and switching VOICE_ENABLED=false is enough to stop synthesis.
```

## Rules this repo assumes you follow

1. **Do not commit voice artifacts.** `voiceprint/` is gitignored: reference
   audio, clips and `latents.pt` stay on the machine that made them. Publishing
   a repo does not publish a voice, and it should stay that way.
2. **Tell listeners it is synthetic.** A bot in a Discord channel should be
   recognisable as a bot, not mistaken for the person it sounds like.
3. **Never clone a voice to impersonate someone** — not to move money, not to
   pass identity checks, not to put words in someone's mouth. That is fraud
   wherever you live, and the person's consent to a friendly bot is not consent
   to that.
4. **Honour withdrawal immediately.** Consent given once is not permanent.

If you cannot get consent, use your own voice. The setup is identical.
