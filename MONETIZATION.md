# Monetization

**Money comes from YouTube and Substack. Nothing else.**

YouTube: ad revenue and channel membership. Substack: paid subscriptions.

Every other destination is distribution, not revenue. X, LinkedIn, Facebook, Telegram, WhatsApp
and the site exist to move people to the channel or to the newsletter. They never sell anything
themselves and they never carry a paywall.

## What follows from this

* **Two destinations get the full treatment, the rest get a link.** A clip that is not going to
  YouTube or Substack does not need to earn anything on its own. It needs to point somewhere.
* **The paid tier lives on Substack.** `paid_only_for_live: true` in the profile config already
  says this: live Q&A is subscriber content, clips are not.
* **YouTube monetization and step 0 pull in opposite directions.** Ads on a video mean claiming
  the revenue from it. Broadcaster footage is exactly what you cannot claim revenue on: a
  Content ID claim redirects the money to the claimant, and `--mode appearance` exists because
  some material cannot be uploaded at all. Own recordings monetize. Appearances link.
* **Do not add a third rail.** Every new platform with a tip jar is another account to keep
  alive for a rounding error. If one is ever added, it replaces one of these two rather than
  joining them.

## Open

`link_block()` in `lib/common.py` appends Ko-fi, PayPal and an IBAN to every post on every
network. Those are direct-donation rails, which is a third source of money, and this document
says there are two. Either they are an exception worth stating here, or they come out of the
link block. Not decided.
