# Connecting to Facebook

One-time setup so this machine can post to the Facebook **Page**. About fifteen minutes. No
server, no domain, no App Review: everything is done in Graph API Explorer, and the token you
end up with does not expire.

A personal profile cannot be posted to by any API. Only a Page. If Tom posts from a personal
profile today, make a Page first.

---

## 1. Create an app

[developers.facebook.com](https://developers.facebook.com) → **My Apps** → **Create App**.

* Use case: **Other** → app type **Business**.
* Name it anything. Create.

You do not need to configure any products. The app exists only so Graph API Explorer has
something to issue tokens against.

## 2. Get a user token with the right permissions

**Tools → Graph API Explorer** (top right menu, or developers.facebook.com/tools/explorer).

* **Meta App**: pick the app you just made.
* **User or Page**: leave as *User Token*.
* **Permissions**: add these three:
  * `pages_show_list`
  * `pages_read_engagement`
  * `pages_manage_posts` ← this is the one that actually allows publishing
* Press **Generate Access Token**, sign in, and grant access **to the specific Page**.

You now have a short-lived **user** token, good for about an hour. It is not the one you want,
but it is how you get the one you want.

## 3. Find the Page and its own token

Still in the Explorer, put this in the request box and press Submit:

```
me/accounts
```

The response lists every Page you administer. Find yours and note two fields:

* `id` → this is your **FB_PAGE_ID**
* `access_token` → a **Page** token, different from the user token

If the list is empty, you are not an admin of any Page, or you did not grant the app access to
the Page in step 2.

## 4. Make the token permanent

The Page token from step 3 inherits the user token's short life. Two calls fix that for good.

First, exchange the short-lived user token for a long-lived one. You need your **App ID** and
**App Secret** from **App settings → Basic** in the app dashboard.

```
GET /oauth/access_token
    ?grant_type=fb_exchange_token
    &client_id=<APP_ID>
    &client_secret=<APP_SECRET>
    &fb_exchange_token=<SHORT_LIVED_USER_TOKEN>
```

Paste that path into the Explorer request box (everything after `/`), submit, and copy the
`access_token` it returns. That is a long-lived user token, about 60 days.

Now call `me/accounts` **again**, this time with the long-lived user token selected. The Page
token it returns this time **never expires**, as long as you remain an admin of the Page.

## 5. Put them in .env

```
FB_PAGE_ID=1234567890
FB_PAGE_TOKEN=EAAG...
```

`.env` is gitignored. A Page token is a password: it does not expire, so anyone holding it can
post as the Page indefinitely.

## 6. Check it

```
cd ~/Desktop/crosspost-studio
PYTHONPATH=lib .venv/bin/python lib/facebook_post.py --check
```

Prints the Page name, follower count, whether the token expires, and which permissions it
carries. If it says the token expires, step 4 did not take: you called `me/accounts` with the
short-lived token again.

---

## Posting

```
# text and a link — the safe form for someone else's footage
PYTHONPATH=lib .venv/bin/python lib/facebook_post.py \
  --message "..." --link "https://vijesti.hrt.hr/..."

# a video, once you have permission to re-upload
PYTHONPATH=lib .venv/bin/python lib/facebook_post.py \
  --message "..." --video work/<slug>/whatsapp/short_1.wa.mp4 --title "Naslov"
```

It asks before publishing. `--yes` skips that once you trust it.

---

## When it stops working

The script translates the common Graph error codes, but for reference:

| Code | Meaning |
|---|---|
| 190 | Token expired or revoked. Redo step 4, or you were removed as Page admin. |
| 200 | Missing permission. The token lacks `pages_manage_posts`; redo step 2. |
| 100 | Bad parameter. Usually `FB_PAGE_ID` holds the app id instead of the Page id. |
| 368 | The Page is temporarily blocked from posting, normally after spam reports. |

Changing your Facebook password invalidates every token. So does removing the app under
**Settings → Security → Business Integrations**. Both mean redoing steps 2 to 4.

---

## Before posting someone else's video

Uploading a broadcaster's footage to a Page is publishing it, and Facebook runs Rights Manager
much as YouTube runs Content ID. Without written permission, post the text and a link instead:
that is what `--link` is for, and it needs no upload. See step 0 of
`HOW-THIS-IS-INTENDED-TO-WORK.md`.
