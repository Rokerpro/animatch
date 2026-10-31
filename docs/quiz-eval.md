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

Methods A and B are printed side by side by every start demo. Method A blends raw cosine scores from the quiz vector and the normalized liked-title vector. Method B first rank-normalizes each liked-title score across eligible candidates, averages those ranks, and adds a small bonus for candidates ranking in the top quartile for at least two liked titles. It also rank-normalizes quiz scores before blending. Thus `REC_START_LIKED_WEIGHT` (default `0.7`) is the actual share of the liked signal in Method B's blend. The default is currently B (`REC_START_METHOD=B`), pending review of mixed-taste outputs; this is not a validated quality conclusion. Inspect whether B over-rewards candidates fitting multiple seeds or whether A's vector average blurs distinct tastes.
Liked: ['Attack on Titan', 'Death Note', 'Laid-Back Camp']; quiz-set=None; scoring methods A and B

Method A
1. BABYLON | 2019 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Thriller, Crime.
2. ERASED | 2016 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Supernatural, Thriller.
3. SHOSHIMIN: How to Become Ordinary | 2024 | TV | Slice of Life, Mystery | Because you liked Attack on Titan, Laid-Back Camp: shares Mystery, Primarily Teen Cast, Male Protagonist, Slice of Life.
4. Talentless Nana | 2020 | TV | Drama, Supernatural, Thriller, Mystery, Horror, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Supernatural, Thriller.
5. Paranoia Agent | 2004 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Supernatural, Thriller.
6. Haibane Renmei | 2002 | TV | Drama, Slice of Life, Fantasy, Mystery, Psychological | Because you liked Attack on Titan, Death Note: shares Drama, Fantasy, Mystery, Coming of Age.
7. Terror in Resonance | 2014 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Thriller, Crime.
8. the Garden of sinners Chapter 1: Thanatos. (Overlooking View) | 2007 | MOVIE | Action, Supernatural, Thriller, Mystery | Because you liked Death Note, Attack on Titan: shares Mystery, Supernatural, Thriller, Philosophy.
9. B: The Beginning | 2018 | ONA | Action, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Supernatural, Thriller.
10. Monster | 2004 | TV | Drama, Thriller, Mystery, Horror, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Thriller, Crime.

Method B
1. SHOSHIMIN: How to Become Ordinary | 2024 | TV | Slice of Life, Mystery | Because you liked Attack on Titan, Laid-Back Camp: shares Mystery, Primarily Teen Cast, Male Protagonist, Slice of Life.
2. Haibane Renmei | 2002 | TV | Drama, Slice of Life, Fantasy, Mystery, Psychological | Because you liked Attack on Titan, Death Note: shares Drama, Fantasy, Mystery, Coming of Age.
3. Eden of the East | 2009 | TV | Drama, Thriller, Sci-Fi, Romance, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Thriller, Male Protagonist.
4. Rewrite | 2016 | TV | Drama, Supernatural, Slice of Life, Romance, Mystery | Because you liked Attack on Titan, Death Note: shares Drama, Mystery, Male Protagonist, Supernatural.
5. BEASTARS | 2019 | TV | Drama, Slice of Life, Romance, Mystery, Psychological | Because you liked Death Note, Attack on Titan: shares Mystery, Psychological, Male Protagonist, Philosophy.
6. ACCA: 13-Territory Inspection Dept. | 2017 | TV | Drama, Slice of Life, Mystery | Because you liked Attack on Titan, Death Note: shares Drama, Mystery, Male Protagonist, Ensemble Cast.
7. MUSHI-SHI | 2005 | TV | Adventure, Supernatural, Slice of Life, Fantasy, Mystery, Psychological | Because you liked Death Note, Laid-Back Camp: shares Mystery, Psychological, Supernatural, Male Protagonist.
8. Spy Classroom | 2023 | TV | Drama, Comedy, Action, Mystery | Because you liked Attack on Titan, Death Note: shares Action, Drama, Mystery, Male Protagonist.
9. Migi&Dali | 2023 | TV | Drama, Slice of Life, Mystery | Because you liked Attack on Titan, Death Note: shares Drama, Mystery, Male Protagonist.
10. WorldEnd: What are you doing at the end of the world? Are you busy? Will you save us? | 2017 | TV | Drama, Supernatural, Slice of Life, Fantasy, Romance, Mystery | Because you liked Attack on Titan, Death Note: shares Drama, Fantasy, Mystery, Military.
Liked: ['Death Note', 'Monster', 'Psycho-Pass']; quiz-set=None; scoring methods A and B

Method A
1. Moriarty the Patriot | 2020 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Monster, Death Note: shares Drama, Mystery, Psychological, Thriller.
2. B: The Beginning | 2018 | ONA | Action, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, PSYCHO-PASS: shares Mystery, Psychological, Supernatural, Thriller.
3. Terror in Resonance | 2014 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
4. ID: INVADED | 2020 | TV | Drama, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
5. BABYLON | 2019 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
6. PLUTO | 2023 | ONA | Mecha, Drama, Action, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Monster: shares Action, Psychological, Sci-Fi, Thriller.
7. Paranoia Agent | 2004 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Supernatural, Thriller.
8. Talentless Nana | 2020 | TV | Drama, Supernatural, Thriller, Mystery, Horror, Psychological | Because you liked Monster, Death Note: shares Drama, Horror, Mystery, Psychological.
9. The Perfect Insider | 2015 | TV | Drama, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
10. ODDTAXI | 2021 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.

Method B
1. Moriarty the Patriot | 2020 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Monster, Death Note: shares Drama, Mystery, Psychological, Thriller.
2. Fate/stay night | 2006 | TV | Action, Supernatural, Fantasy, Romance | Because you liked Death Note, PSYCHO-PASS: shares Supernatural, Male Protagonist, Urban Fantasy, Urban.
3. ID: INVADED | 2020 | TV | Drama, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
4. Terror in Resonance | 2014 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
5. PLUTO | 2023 | ONA | Mecha, Drama, Action, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Monster: shares Action, Psychological, Sci-Fi, Thriller.
6. B: The Beginning | 2018 | ONA | Action, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, PSYCHO-PASS: shares Mystery, Psychological, Supernatural, Thriller.
7. ODDTAXI | 2021 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
8. Lupin the 3rd | 1971 | TV | Adventure, Comedy | Because you liked PSYCHO-PASS, Death Note: shares Detective, Police, Crime, Primarily Adult Cast.
9. Paranoia Agent | 2004 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Supernatural, Thriller.
10. Paprika | 2006 | MOVIE | Fantasy, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
Liked: ['Laid-Back Camp', 'Non Non Biyori', 'Barakamon']; quiz-set=None; scoring methods A and B

Method A
1. Akebi’s Sailor Uniform | 2022 | TV | Slice of Life | Because you liked Non Non Biyori, Barakamon: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Rural.
2. Super Cub | 2021 | TV | Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Rural.
3. Mitsuboshi Colors | 2018 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Outdoor Activities, Iyashikei.
4. Deaimon: Recipe for Happiness | 2022 | TV | Slice of Life | Because you liked Barakamon, Non Non Biyori: shares Slice of Life, Found Family, Iyashikei, Episodic.
5. Is the Order a Rabbit? | 2014 | TV | Slice of Life | Because you liked Non Non Biyori, Barakamon: shares Slice of Life, Cute Girls Doing Cute Things, Female Protagonist, Primarily Female Cast.
6. Do It Yourself!! | 2022 | TV | Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Female Protagonist.
7. Yuyushiki | 2013 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Iyashikei, Cute Girls Doing Cute Things.
8. Azumanga Daioh | 2002 | TV | Comedy, Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Female Protagonist, Primarily Female Cast.
9. Tanaka-kun is Always Listless | 2016 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Iyashikei, Primarily Teen Cast.
10. Strawberry Marshmallow | 2005 | TV | Comedy, Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Female Protagonist.

Method B
1. Super Cub | 2021 | TV | Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Rural.
2. Azumanga Daioh | 2002 | TV | Comedy, Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Female Protagonist, Primarily Female Cast.
3. Mitsuboshi Colors | 2018 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Outdoor Activities, Iyashikei.
4. Do It Yourself!! | 2022 | TV | Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Female Protagonist.
5. Tanaka-kun is Always Listless | 2016 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Iyashikei, Primarily Teen Cast.
6. Akebi’s Sailor Uniform | 2022 | TV | Slice of Life | Because you liked Non Non Biyori, Barakamon: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Rural.
7. Is the Order a Rabbit? | 2014 | TV | Slice of Life | Because you liked Non Non Biyori, Barakamon: shares Slice of Life, Cute Girls Doing Cute Things, Female Protagonist, Primarily Female Cast.
8. Yuyushiki | 2013 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Iyashikei, Cute Girls Doing Cute Things.
9. Hidamari Sketch | 2007 | TV | Comedy, Slice of Life | Because you liked Non Non Biyori, Laid-Back Camp: shares Slice of Life, Cute Girls Doing Cute Things, Iyashikei, Female Protagonist.
10. Silver Spoon | 2013 | TV | Comedy, Slice of Life | Because you liked Laid-Back Camp, Non Non Biyori: shares Comedy, Slice of Life, Rural, Food.
Title not found: Howl's Moving Castle
Liked: ['Death Note', 'Monster', 'Psycho-Pass']; quiz-set=5; scoring methods A and B

Method A
1. B: The Beginning | 2018 | ONA | Action, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, PSYCHO-PASS: shares Mystery, Psychological, Supernatural, Thriller.
2. Moriarty the Patriot | 2020 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Monster, Death Note: shares Drama, Mystery, Psychological, Thriller.
3. Terror in Resonance | 2014 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
4. ID: INVADED | 2020 | TV | Drama, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
5. PLUTO | 2023 | ONA | Mecha, Drama, Action, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Monster: shares Action, Psychological, Sci-Fi, Thriller.
6. BABYLON | 2019 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
7. Talentless Nana | 2020 | TV | Drama, Supernatural, Thriller, Mystery, Horror, Psychological | Because you liked Monster, Death Note: shares Drama, Horror, Mystery, Psychological.
8. ERASED | 2016 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Supernatural, Thriller.
9. Paprika | 2006 | MOVIE | Fantasy, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
10. Paranoia Agent | 2004 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Supernatural, Thriller.

Method B
1. B: The Beginning | 2018 | ONA | Action, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, PSYCHO-PASS: shares Mystery, Psychological, Supernatural, Thriller.
2. Lupin the 3rd | 1971 | TV | Adventure, Comedy | Because you liked PSYCHO-PASS, Death Note: shares Detective, Police, Crime, Primarily Adult Cast.
3. Moriarty the Patriot | 2020 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Monster, Death Note: shares Drama, Mystery, Psychological, Thriller.
4. PLUTO | 2023 | ONA | Mecha, Drama, Action, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Monster: shares Action, Psychological, Sci-Fi, Thriller.
5. Talentless Nana | 2020 | TV | Drama, Supernatural, Thriller, Mystery, Horror, Psychological | Because you liked Monster, Death Note: shares Drama, Horror, Mystery, Psychological.
6. the Garden of sinners Chapter 1: Thanatos. (Overlooking View) | 2007 | MOVIE | Action, Supernatural, Thriller, Mystery | Because you liked Death Note, Monster: shares Mystery, Supernatural, Thriller, Philosophy.
7. Terror in Resonance | 2014 | TV | Drama, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Thriller, Crime.
8. Tengoku Daimakyo | 2023 | TV | Adventure, Thriller, Sci-Fi, Mystery | Because you liked PSYCHO-PASS, Death Note: shares Sci-Fi, Thriller, Guns, Male Protagonist.
9. ID: INVADED | 2020 | TV | Drama, Thriller, Sci-Fi, Mystery, Psychological | Because you liked PSYCHO-PASS, Death Note: shares Psychological, Sci-Fi, Thriller, Detective.
10. ERASED | 2016 | TV | Drama, Supernatural, Thriller, Mystery, Psychological | Because you liked Death Note, Monster: shares Mystery, Psychological, Supernatural, Thriller.
