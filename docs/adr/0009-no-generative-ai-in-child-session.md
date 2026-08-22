# ADR-0009: No conversational or generative AI in the child-facing system

- Status: accepted; revisit annually (next: 2027-08)
- Date: 2026-08-22

## Context

*06 §e*, *02 §4 #10*, *03 §2.6/§2.12*: the 2026 evidence on generative AI for
young children is uniformly negative or absent — EYSTAG (DfE/DHSC, March 2026)
advises parents not to let young children use AI tools, toys or chatbots "until
the present state of knowledge improves"; the FTC issued 6(b) orders to seven
AI-companion companies (Sept 2025); Common Sense Media rates social AI
companions "Unacceptable" for under-18s; PIRG's AI-toy testing found toys
calling themselves the child's friend, expressing dismay when left, guardrails
degrading over long conversations; the EU AI Act Art. 5(1)(b) prohibits
exploiting age-related vulnerabilities; no CCI evidence supports open-ended
generative chat for 4–8s. Child ASR is also unsolved (WER 9–35%).

## Decision

1. No conversational LLM, chatbot, "AI tutor", AI companion or generative
   image/text/music model is reachable from the child session — on-device or
   cloud.
2. Deterministic, curated **text-to-speech read-aloud** (speech-dispatcher /
   Piper with a licensed voice) is explicitly fine and is core to the product.
3. Speech *input*, if ever added, is an optional, offline, closed-vocabulary
   accessory (e.g. "say the sound") — never a required path, never free-form.
4. Generative AI may be used by *developers* to build kidnix and by the
   *parent* in their own session; it never touches the child's data without
   explicit parent action.

## Consequences

- A clear, publishable stance ("say so loudly" — *06*), aligned with ICO
  Children's Code best-interests and data-minimisation standards.
- Revisit triggers: EYSTAG/AAP guidance changes; an independent RCT showing
  benefit for 4–8s with a bounded, non-parasocial design; on-device child-ASR
  reaching < 10% WER for UK 5-year-olds.
