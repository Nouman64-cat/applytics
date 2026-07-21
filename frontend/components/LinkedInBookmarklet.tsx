"use client";

// Runs in the BD's own logged-in LinkedIn tab (dragged to the bookmarks bar, not hosted on
// our origin) — copies the visible profile text to the clipboard so it can be pasted into
// the "paste LinkedIn text" box. Never touches our servers or LinkedIn's servers as a bot;
// it's the BD's own authenticated browser session reading a page they're already viewing,
// so it doesn't trigger LinkedIn's bot detection the way direct scraping does.
//
// Deliberately favors grabbing broad visible page text over precise CSS selectors — the
// first version guessed at LinkedIn's specific class names (not verified against a live
// logged-in session) and failed silently with no visible feedback when they didn't match
// and something else threw. Gemini's extraction on the other end already handles noisy,
// loosely-structured text fine, so precision here isn't worth the fragility. Everything is
// wrapped in try/catch so any failure shows a visible alert instead of doing nothing.
const BOOKMARKLET_CODE = `(function(){try{function text(sel){try{var e=document.querySelector(sel);return e&&e.innerText?e.innerText.trim():'';}catch(e){return '';}}var name=text('h1.text-heading-xlarge')||text('.pv-text-details__left-panel h1')||text('h1');var headline=text('.text-body-medium.break-words')||text('.pv-text-details__left-panel .text-body-medium');var loc=text('.text-body-small.inline.t-black--light.break-words')||text('.pv-text-details__left-panel .text-body-small');var about=text('.pv-shared-text-with-see-more .inline-show-more-text')||text('#about ~ * .inline-show-more-text');var parts=[name,headline,loc,about].filter(Boolean);var out=parts.join('\\n');if(out.length<20){var main=document.querySelector('main')||document.body;var broad=(main&&main.innerText?main.innerText:(document.body.innerText||'')).trim();if(broad.length>out.length)out=broad.slice(0,3000);}if(!out){alert('Applytics: found no text on this page. Make sure you are on a LinkedIn profile page and it has fully loaded, then try again.');return;}function done(){alert('Applytics: copied '+out.length+' characters to your clipboard. Now paste it into the Applytics LinkedIn box.');}function fail(){window.prompt('Applytics: could not access the clipboard automatically. Copy this text (Cmd/Ctrl+C), then paste into Applytics:',out);}if(navigator.clipboard&&navigator.clipboard.writeText){navigator.clipboard.writeText(out).then(done,fail);}else{fail();}}catch(err){alert('Applytics bookmarklet error: '+(err&&err.message?err.message:err));}})();`;

export default function LinkedInBookmarklet() {
  return (
    <div className="rounded-md border border-dashed border-zinc-300 p-3 text-xs text-zinc-500 dark:border-zinc-700">
      <p className="mb-2 font-medium text-zinc-600 dark:text-zinc-400">
        Speed up the paste step: drag this to your bookmarks bar.
      </p>
      <a
        href={`javascript:${BOOKMARKLET_CODE}`}
        onClick={(e) => e.preventDefault()}
        draggable
        className="inline-flex cursor-move items-center rounded-md border border-zinc-300 bg-white px-3 py-1.5 text-xs font-medium text-zinc-700 shadow-sm dark:border-zinc-600 dark:bg-zinc-800 dark:text-zinc-200"
      >
        Grab LinkedIn Profile
      </a>
      <p className="mt-2">
        While viewing a candidate&apos;s profile in your own logged-in LinkedIn tab, click it — it copies visible
        profile text to your clipboard (or shows a popup with the text to copy manually if clipboard access is
        blocked). Paste that into the box below. If you installed the button before this update, delete that old
        bookmark and re-drag this one — bookmarklets don&apos;t auto-update.
      </p>
    </div>
  );
}
