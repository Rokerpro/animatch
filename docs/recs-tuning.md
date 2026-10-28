# Recommendation Engine Tuning Backlog

This document captures identified tuning opportunities, feature enhancements, and benchmarking improvements for the AniMatch recommendation engine following the Phase 4 ranking overhaul.

---

## 1. Studio and Director Feature Clustering (Weak Feature Block)

* **Problem**: Same-studio and auteur-driven works currently do not cluster unless their genre and tag sets align closely. For example:
  * *Kiki's Delivery Service* and *Howl's Moving Castle* do not appear in *Spirited Away*'s top recommendations despite shared Studio Ghibli / Hayao Miyazaki stylistic DNA.
  * *Samurai Champloo* (Shinichiro Watanabe) drops out of *Cowboy Bebop*'s top recommendations because historical chambara tags dilute the sci-fi/space tags.
* **Proposal**:
  * Add `main_studio` as a distinct low-weighted one-hot or categorical feature block in `VectorIndex` (e.g., $w_{\text{studio}} \approx 0.05 \text{ to } 0.10$).
  * Optionally ingest primary director metadata from AniList's `staff` edge to cluster auteur filmographies (e.g., Hayao Miyazaki, Shinichiro Watanabe, Satoshi Kon, Makoto Shinkai, Masaaki Yuasa).

---

## 2. Quality Weight Tuning and Seed-Aware Soft Quality Floors

* **Problem**: Setting the additive quality weight to $q = 0.10$ successfully prevented quality from swamping relevance, but in some cases obscure, niche, or mediocre titles outrank landmark classics:
  * For *Attack on Titan*, obscure titles like *To the Abandoned Sacred Beasts* (average score ~63, popularity ~30k) rank ahead of acclaimed high-affinity titles like *Neon Genesis Evangelion* or *Fullmetal Alchemist: Brotherhood*.
  * For *Frieren: Beyond Journey's End*, *Übel Blatt* and *My Daughter Left the Nest and Returned an S-Rank Adventurer* outrank widely loved fantasy companions like *Delicious in Dungeon*.
* **Proposal**:
  * **Tune $q$**: Experiment with increasing the additive weight to $q \in [0.15, 0.25]$.
  * **Seed-Aware Quality Scaling**: For landmark seeds ($S_{\text{seed}} \ge 85$ and high popularity), apply a mild logarithmic popularity/quality dampening on low-scoring candidate items to ensure recommendations match the caliber of the seed.
  * **Soft Quality Floor**: Introduce a soft penalty that scales down candidate relevance when the candidate score is significantly lower than the seed score (e.g., candidate average score $< 70$ when seed is $> 85$).

---

## 3. Post-MMR Selection Score in `recs-demo`

* **Problem**: The `recs-demo` table currently displays `Final` (the pre-MMR score: $s_{\text{sim}} + q \cdot s_{\text{qual}}$) and `PreMMR` rank (`#N`). While position shifts are reported (`[MMR: #3→#2]`), the actual marginal selection value computed by MMR at selection time is not visible.
* **Proposal**:
  * Record the marginal MMR objective value:
    $$\text{score}_{\text{MMR}}(i) = \lambda \cdot s_{\text{relevance}}(i) - (1 - \lambda) \cdot \max_{j \in S} \text{Sim}(i, j)$$
  * Expose this score in `RecResult` and add a column to `recs-demo` to make diversity trade-offs and penalties explicit.

---

## 4. Fixed "Golden Seeds" Evaluation Benchmark

* **Problem**: Engine tuning currently relies on manual qualitative inspection of terminal outputs across a handful of titles, which is prone to subjective bias and regression blind spots.
* **Proposal**:
  * Establish a version-controlled benchmark dataset (`docs/golden_seeds.json` or `backend/tests/fixtures/golden_seeds.json`) specifying 15–20 landmark seeds and their expected high-affinity neighbors:
    * **Frieren: Beyond Journey's End** $\rightarrow$ *Delicious in Dungeon*, *Mushoku Tensei*, *Spice and Wolf*, *To Your Eternity*.
    * **Death Note** $\rightarrow$ *Monster*, *Code Geass*, *Psycho-Pass*, *ERASED*, *Moriarty the Patriot*.
    * **Cowboy Bebop** $\rightarrow$ *Trigun*, *Samurai Champloo*, *Space Dandy*, *Michiko & Hatchin*, *Black Lagoon*.
    * **Spirited Away** $\rightarrow$ *Princess Mononoke*, *Howl's Moving Castle*, *My Neighbor Totoro*, *The Boy and the Beast*.
    * **Laid-Back Camp** $\rightarrow$ *Non Non Biyori*, *A Place Further Than the Universe*, *Super Cub*, *Yama no Susume*.
    * **Attack on Titan** $\rightarrow$ *Kabaneri of the Iron Fortress*, *Vinland Saga*, *Neon Genesis Evangelion*, *86*.
  * Add an automated evaluation script/metric (e.g., Mean Reciprocal Rank or Recall@10 against the golden sets) to quantify tuning gains across parameter sweeps.

---

## 5. Re-Evaluation with Real User Ratings and MAL Imports

* **Problem**: Current profile personalization testing is performed against synthetic rating distributions and centered user means.
* **Proposal**:
  * Once Phase 5 (user list imports from MyAnimeList/AniList) is active and real multi-title user profiles exist:
    * Re-evaluate rating centering variance ($\sigma_r > 0$) behavior on genuine large watchlists (100+ titles).
    * Evaluate cold-start hybrid decay ($K = 10$) with authentic incremental ratings.
    * Calibrate profile diversity ($\lambda_{\text{profile}}$) vs. seed similarity diversity ($\lambda_{\text{seed}}$).
