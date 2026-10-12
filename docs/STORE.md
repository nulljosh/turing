# App Store plan for Samantha ($1)

Nothing here is submitted. This is the listing, the answers Apple will ask for, and what blocks each step, so a submission is an afternoon and not a week. Name, price and age rating go through the asc skills (asc-name-creator, apple-pricing) at the time, never by hand.

## What the listing leads with

On-device and tools. She is a small assistant that runs on your own Mac or iPhone, picks a tool, and does the thing: files, calendar, reminders, mail drafts, code, Shortcuts you add yourself. Nimble is the more polished sibling; Samantha sells the part Nimble does not, her hands and her memory.

- Subtitle idea: "Her hands are on your Mac" (check the 30 character limit and the single-word naming rule when the name is chosen).
- Promotional text: what shipped this week, in two plain sentences.
- Keywords: on-device assistant, local AI, Mac assistant, Shortcuts, private, memory.
- Price: $1 upfront, free of in-app purchases, same as the rest of the fleet (GTM.md, apple-pricing skill).

## Answers Apple will ask for

- **Account or sign-in:** none. Review notes must say so, so no demo account is needed.
- **Data collection:** the apps collect nothing. The landing demo's Cloudflare Worker is the website, not the app; the privacy policy page (web/privacy.html) says what each part does. Declare "Data Not Collected" for the apps only if the shipped builds make no network calls of their own; the iPhone app's Hugging Face model download and the paired-Mac bridge are the two to describe in the notes.
- **Encryption:** the app uses standard HTTPS and Apple's CryptoKit for signed requests. Answer the export compliance question with the exempt category after reading the current Apple text, and add ITSAppUsesNonExemptEncryption to Info.plist.
- **Age rating:** run the asc questionnaire honestly. She can write code and read files the person points her at; she asks first before anything that writes. No user-generated content shared between people.
- **Privacy policy URL:** https://turing.heyitsmejosh.com/privacy.html
- **Review notes:** say what to try (the first run downloads her models, about two minutes on the Mac and a larger download on the phone), that every write asks first, and that a Shortcut she makes is a file the reviewer adds themselves.

## What blocks each platform

- **Mac:** the store build must be the native SwiftUI target, signed for the store (the Developer ID zip is for the website download). The MLX path inside a sandbox is unverified; test it before committing to the store build.
- **iPhone:** no signed device build exists yet; the simulator build compiles. A device build, the iCloud entitlement for memory sync, and a TestFlight run are needed first. Joshua does the signing.
- **Both:** bundle id com.nulljosh.samantha is not yet in App Store Connect. Screenshots come from the simulator and the Mac app, taken after the QA videos grade A or better. No demo accounts.

## Order of work

1. QA the three surfaces to A or better (iOS, Mac, website).
2. A signed device build and a TestFlight pass (Joshua).
3. Create the ASC record with the name from asc-name-creator, set the $1 price, fill the answers above.
4. Submit iPhone first, Mac after, and never resubmit into a rejection without reading Resolution Center.
