# Recommendation quality evaluation

Run these commands from `backend/` on a machine with the local catalog database. Append the complete terminal output to this file before writing the qualitative assessment. Catalog-specific output cannot be generated in the restricted sandbox.

```sh
python -m app.cli quiz-demo | tee -a ../docs/quiz-eval.md
python -m app.cli start-demo --liked "Death Note" --liked "Monster" --liked "Psycho-Pass" | tee -a ../docs/quiz-eval.md
python -m app.cli start-demo --liked "Laid-Back Camp" --liked "Non Non Biyori" --liked "Barakamon" | tee -a ../docs/quiz-eval.md
python -m app.cli start-demo --liked "Attack on Titan" --liked "Death Note" --liked "Laid-Back Camp" | tee -a ../docs/quiz-eval.md
python -m app.cli start-demo --liked "Spirited Away" --liked "Howl's Moving Castle" --liked "Your Name" | tee -a ../docs/quiz-eval.md
python -m app.cli start-demo --liked "Death Note" --liked "Monster" --liked "Psycho-Pass" --quiz-set 5 | tee -a ../docs/quiz-eval.md
```

## Quiz sets

1. Dark psychological thrillers: mood `tense`, pacing `balanced`, tone `dark`, themes `mystery`, intensity `intense`, length/era `any`.
2. Cozy slice of life: mood `cozy`, pacing `slow`, tone `hopeful`, themes `slice_of_life`, intensity `chill`, length/era `any`.
3. Epic fantasy adventure: mood `epic`, pacing `fast`, tone `hopeful`, themes `fantasy`, intensity `intense`, length `long`, era `any`.
4. Romance and school life: mood `emotional`, pacing `balanced`, tone `romantic`, themes `slice_of_life`, intensity `moderate`, length `medium`, era `any`.
5. Action-packed shounen: mood `epic`, pacing `fast`, tone `hopeful`, themes `mystery`, intensity `intense`, length `long`, era `any`.
6. Sci-fi and mecha: mood `epic`, pacing `fast`, tone `dark`, themes `sci_fi`, intensity `intense`, length `medium`, era `any`.

## Assessment

Pending local catalog output. No quality judgments are claimed without inspecting the recommendations. Do not change quiz weights or `quiz.json` based on this placeholder; propose any changes after reviewing the appended results.

## Start scoring comparison

Methods A and B are printed side by side by every start demo. The default is currently B (`REC_START_METHOD=B`): it preserves per-seed rankings across differently distributed similarity scores and adds a small shared-fit bonus. This is an implementation choice pending review of the mixed-taste outputs, not a validated quality conclusion. Inspect whether B over-rewards candidates that fit only one seed or whether A's vector average blurs distinct tastes.
