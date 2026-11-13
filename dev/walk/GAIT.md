# Dog walk: reference numbers and images (research pass, 2026-11-12)

Scope: side view of a medium dog at a slow to normal walk. Every number carries its source. "[est]" marks my own estimate or
standard textbook knowledge that I did not verify in a fetched source. "[gap]" marks a number I looked for and did not find.
Sources that blocked fetching (PMC web pages, Springer HTML, ResearchGate, the Maes 2008 JEB PDF, Hildebrand 1968 full text)
were not read; the papers used were read through the Europe PMC full-text API (open-access XML) and the Springer figure server.

## Sources actually read

- S1. Fischer MS, Lehmann SV, Andrada E (2018) "Three-dimensional kinematics of canine hind limbs: in vivo, biplanar, high-frequency
  fluoroscopic analysis of four breeds during walking and trotting", Sci Rep 8:16982, doi 10.1038/s41598-018-34310-0, CC BY.
  Whippet, French Bulldog, Malinois, Beagle; walk and trot; X-ray ("scientific rotoscoping") plus markers. Tables 1-3 and Figs 1-2
  read in full. This is the Jena group that wrote "Dogs in Motion" (Fischer & Lilje 2011).
- S2. Catavitello G, Ivanenko YP, Lacquaniti F (2015) PLoS ONE 10(7):e0133936, "Planar covariation of hindlimb and forelimb elevation
  angles during terrestrial and aquatic locomotion of dogs", CC BY. Six Golden/Labrador Retrievers, walk/trot/gallop/swim.
  Text read; the figure values (Fig 1C-E, 2, 3B) were not readable, only the text.
- S3. Gustas et al. (2016) Acta Vet Scand 58:78, treadmill habituation in 25 Labradors at 0.78 and 0.96 m/s. Text read; its tables
  hold only p-value/time-to-stabilise data, no gait numbers.
- S4. Clarke et al. (2024) Heliyon 10:e40952, cavaletti study, CC BY; floor-height (flat walking) control values used.
- S5. Phys.org / Univ. Jena press release (2011-05-27) "Dogs in motion" (PDF read) about Fischer & Lilje.
- S6. julius-k9.com page summarising Fischer & Lilje (secondary).
- S7. Original Wisdom summary page of Hildebrand (1968) "Symmetrical gaits of dogs in relation to body build" (secondary; full text
  was not served).
- S8. Frontiers Vet Sci 2026, doi 10.3389/fvets.2026.1878605 (German Shepherds): quantitative results are trot only.

## (a) Footfall order, phases, duty factors

| Item | Value | Source / quote |
|---|---|---|
| Gait type | Lateral-sequence walk, 1:1 limb frequency | S2: "all dogs displayed a lateral sequence walk, a trot with synchronized diagonal limb movements and a transverse gallop" and "the canine gait pattern ranged from a lateral sequence of footfalls during walking to a diagonal sequence in trotting and swimming" |
| Footfall order | RH, RF, LH, LF (then repeat); each hind is followed by the fore of the SAME side | Common veterinary/animal-gait statement (search-result snippets, several sites). Not primary-sourced. Same order as S2's "lateral sequence". |
| Left-right lag within a pair | Fore: 49.8 +/- 1.9 % of the cycle; hind: 50.2 +/- 1.3 % (walk, trot, swim pooled) | S2: "PLs were on average 49.8+/-1.9% for FLs and 50.2+/-1.3% for HLs for walking, trotting and swimming" |
| Lag between a hind touchdown and the same-side fore touchdown | [gap] Not in any text I could read (S2 shows it in Fig 3B only). Textbook ideal for an evenly spaced "single-foot" walk is 25 % [est]. | S7 (Hildebrand): "Long-legged breeds tended to use lateral-couplets gaits at the moderate walk"; "Short-legged breeds tended to use single-foot gaits (all four footfalls evenly spaced)". So a long-legged dog's same-side hind and fore touch closer together than 25 %; a short-legged dog's are evenly spaced. "least marked at slow speeds" (S7). |
| Feet on the ground | 2 or 3 at every moment at a normal walk; 3 feet most of the time. With duty factor > 0.5 there is no moment with fewer than 2 feet and, with an even 25 % spacing and duty ~0.6-0.65, 3 feet are down about 60-80 % of the cycle and 2 (a diagonal pair or a same-side pair) the rest [est, arithmetic from the duty factors below]. | Search-result snippet: "when a dog is walking, there are either two or three feet on the ground at any given time" (not primary). S8: walking "was identified by a three-limb support pattern". |
| Duty factor, hind foot, walk | 0.56-0.64 (fluoroscopy session: Malinois 0.58, Whippet 0.60, Fr. Bulldog 0.63, Beagle 0.60; marker session: Malinois 0.64, Whippet 0.56, Fr. Bulldog 0.56) | S1: "mean speed +/- SD and mean duty factor +/- SD at walk (w) and trot (t) were: Malinois: (w. 1.3 +/- 0.25 m/s, 0.58 +/- 0.02), (t. 2.3 +/- 0.32 m/s, 0.42 +/- 0.03); Whippet: (w. 0.9 +/- 0.1 m/s, 0.6 +/- 0.03) ...; French Bulldog: (w. 0.7 +/- 0.05 m/s, 0.63 +/- 0.05) ...; Beagle: (w. 0.8 +/- 0 m/s, 0.6 +/- 0.03)" |
| Duty factor, fore foot, walk | Same as hind on average | S7 (Hildebrand): "At the walk, forefoot contacts lasted 86% to 109% of hind foot contacts (90 records); on average they were equal." |
| Stance as fraction of cycle (hind), from the toe-off line in S1 Fig 1 | Toe-off at about 58-60 % of the stride in Whippet/Malinois/Beagle; 68 % in the French Bulldog (slow, 0.7 m/s) | S1 Fig 1/2, vertical lines at ~58-60 and 68 on the walk plots (read by eye from the figure) |
| Slow vs normal walk | Slower walk = longer stance. French Bulldog at 0.7 m/s: duty 0.63; Whippet at 0.9: 0.60; Malinois at 1.3: 0.58 (fluoroscopy). Trend is monotonic with speed. | S1 (the four lines above) |
| "Slow walk" duty factor above 0.65 | [gap] No dog source read gives it. Hildebrand's graphs go to ~0.75 for slow walks in other animals; for dogs: "Dogs do not usually walk slower than shown on his graph" (S7), i.e. dogs rarely walk very slowly; a relaxed dog's walk is already in the 0.6-0.65 range. | |
| Duration of rearward limb motion at walk | > 50 % of the cycle, all gaits other than walk < 50 % | S2: "During walking, the relative duration of rearward limb movement was longer than 50% of gait cycle, while for all the other gaits it was less than 50%" |
| Walk speeds measured | Labrador treadmill 0.78 and 0.96 m/s (S3); Malinois 1.2-1.3, Whippet 0.9-1.0, Beagle 0.8-1.0, Fr. Bulldog 0.7-0.8 m/s (S1); Labrador craniocervical study mean 0.98 +/- 0.2 m/s (search-result snippet) | |

### The four footfalls on a 0-100 % cycle (my table, derived)
Cycle starts at right hind touchdown. Using an even 25 % spacing [est; real dogs are lateral-couplet, Hildebrand]:

| % of cycle | event |
|---|---|
| 0 | RH touches down |
| ~25 | RF touches down (same-side fore after the hind; a long-legged dog: ~15-20 [est]) |
| ~50 | LH touches down (S2: left/right hind lag 50.2 %) |
| ~75 | LF touches down (S2: fore pair lag 49.8 %) |
| 0 + 0.60 (S1) | RH lifts off (hind stance 58-64 %); each foot lifts ~60 % of a cycle after its own touchdown |

## (b) Joint pose through the stride

### HINDLIMB, walk (S1, Tables 1 and Figs 1-2; ground truth for this limb)
How S1's angles work (verified by recomputing the table): segment angles are measured from the vertical, positive = distal end
ahead of the proximal end (protraction), negative = behind (retraction). Joint angles shown in the tables are the included
deviation from a straight limb: stifle angle = femur angle minus tibia angle (Whippet walk TD: 44 minus -7.5 = ~52 matches the
table's -51.8; swing 50 %: 32 minus -45.5 = 77.5 matches -77.1). Hock angle = tibia minus metatarsus segment angle (TD: -7.5 minus ~+40
= ~47 matches Fig 2's hock curve at ~46 at 0 %). The paper's own caption says positive = flexion, but the plotted hip and stifle values are
negative; I treat the magnitude as the amount of bend away from straight and say so. Columns are the paper's: stance 0, 25, 50,
75 %, toe-off (TO), then swing 25, 50, 75 %.

Femur (thigh) segment angle, degrees from vertical, + = knee ahead of hip:

| Breed (walk) | TD | st 25 | st 50 | st 75 | TO | sw 25 | sw 50 | sw 75 |
|---|---|---|---|---|---|---|---|---|
| Whippet | 44 | 33 | 21 | 8 | 2 | 14 | 32 | 44 |
| Fr. Bulldog | 52 | 39 | 26 | 10 | 15 | 34 | 51 | 58 |
| Malinois | 48 | 37 | 24 | 8 | -1 | 14 | 38 | 50 |
| Beagle | 52 | 39 | 23 | 9 | 0 | 11 | 32 | 48 |

Tibia (shank) segment angle (Whippet / Fr. Bulldog / Beagle; Malinois tibia is marker-only):

| Breed | TD | st 25 | st 50 | st 75 | TO | sw 25 | sw 50 | sw 75 |
|---|---|---|---|---|---|---|---|---|
| Whippet | -7.5 | -21 | -35 | -46 | -55 | -58 | -46 | -22 |
| Fr. Bulldog | -1 | -18 | -34 | -45 | -57 | -56 | -37 | -13 |
| Beagle | +5 | -10 | -25 | -39 | -50 | -55 | -45 | -18 |

Stifle bend (degrees away from straight; Whippet / Fr. Bulldog / Beagle):

| Breed | TD | st 25 | st 50 | st 75 | TO | sw 25 | sw 50 | sw 75 |
|---|---|---|---|---|---|---|---|---|
| Whippet | 52 | 55 | 58 | 55 | 56 | 71 | 77 | 66 |
| Fr. Bulldog | 52 | 58 | 60 | 52 | 69 | 87 | 86 | 69 |
| Beagle | 41 | 45 | 46 | 43 | 45 | 60 | 70 | 59 |

Hip angle (extension from reference pose; Malinois/Whippet): TD -6 to -8, st 25 -16, st 50 -26, st 75 -42 to -45, TO -47 to -55,
sw 25 -34 to -37, sw 50 -6 to -16, sw 75 -2 to -4. The hip extends steadily through stance, the extension is largest at toe-off, and is
undone in the first half of swing.

Metatarsus (foot) segment angle and hock bend, read from S1 Fig 1 (bottom row) and Fig 2 (hock, bottom row) by eye (+-3 degrees):

| Moment | Metatarsus angle from vertical | Hock bend (tibia-metatarsus) |
|---|---|---|
| TD (0 %) | about +40 to +45 (paw ahead of the hock, metatarsus slanting forward-down) | about 46-50 |
| 10 % stride | ~+40 | ~58-60 (short extra flexion just after touchdown, "the hock joint exhibits a short period of flexion at the beginning of the stance phase") |
| mid-stance (~30 %) | ~+10 to +20 | ~50 |
| TO (58-60 %) | about -20 (Whippet, Bulldog) to -35 (Malinois, Beagle): paw trails behind the hock, heel off | about 26-35 (the most extended hock of the cycle) |
| 70-80 % (mid-swing) | rising quickly through 0 | peak ~62-66 at ~80 % of the stride |
| 90-100 % | +35 to +45 | back to 40-45, then 46 at TD |

S1 text on timing: "Flexion of the hock joint starts late in the swing phase and continues into the first quarter of the stance phase in all breeds but
the French bulldog"; "Flexion of the stifle joint starts earlier than that of the hock joint in the last quarter of the swing phase and continues in all breeds for about the
first two thirds of the stance phase, after which extension begins. Extension of the hip joint starts in the last third of the swing phase and ends shortly before toe-off." [Note: the first sentence as printed seems to
say "swing" where the plotted data show the hock and stifle FLEXING MOST in the swing: hock peak ~80 % of the stride, stifle peak ~75-80 %. I follow the plotted numbers.]

Hip protraction-retraction "effective angular movements" (TD minus TO) at walk: "hip joint during walk/trot: Malinois 47/48, Whippet 41/43, Beagle 41/40
and French bulldog 36/41"; stifle "Whippet 5/4, Beagle 4/2 and French bulldog 14/1" (S1).
S1 on pelvis: "The pelvis shows a pronounced biphasic pattern ('pitch')". Pelvis tilt amplitude in the walk is small (a few degrees: Whippet 48-50, Malinois 50-56).

Retraction/protraction summary (hind), for a side-view rig: the thigh swings from ~+48 degrees ahead of vertical at TD to ~0 (vertical) at TO, so
the thigh is never swung behind the hip's vertical in a walk; the tibia swings from ~0 to ~-55; the metatarsus from ~+40 to ~-20/-35.
Paw lands under/in front of the hip and leaves behind the hip because the shank and foot continue to rotate after the thigh has stopped.

### FORELIMB, walk
Quantitative sagittal angles at TD / mid-stance / TO for shoulder, elbow, carpus: [gap]. Every source that has them (Andrada et al.
2017 Am J Vet Res 78:804; Fischer & Lilje 2011; Hottinger/Gillette 2D link-segment papers) was behind a paywall or blocked. What I did get:

| Fact | Value | Source / quote |
|---|---|---|
| The scapula is the pivot, the shoulder joint barely moves | scapula rotates ~35 degrees as the foreleg goes forward; scapula 24-34 % of foreleg length; humerus is "exactly 27 percent" of foreleg length in every breed | S5: "the actual shoulder joint stays nearly immobile in the dogs' process of movement"; "Regarding the total length of a foreleg its length is always exactly 27 percent"; S6: "the shoulder blade rotates by about 35 degrees when the foreleg is moved forward" |
| Pantograph rule | scapula and forearm are parallel; thigh and metatarsus are parallel (if the forearm is vertical, the scapula is vertical too) | S5: "If the forearm is in a vertical position, then the shoulder blade will be in the same position"; S6: "the shoulder blade/forearm and thigh/midfoot move as if they were wired parallel". Check against S1 hind data: at TD femur +48, metatarsus +40; at TO femur ~0, metatarsus -20/-35: roughly parallel, as stated. |
| Hip and shoulder are NOT at the same height | the hip joint is at the level of the upper edge of the shoulder joint | S6: "in reality the hip joint is at the level of the upper edge of the shoulder joint"; S5: "The displays position the hip and shoulder joint of the animals on the same level... which is wrong" |
| Joint range of motion over a stride, flat floor, normal walking, 8 mixed small/medium dogs (Bodeguero, Cocker, Terriers, Husky x Lab 21.5 kg, Pug) | shoulder 26.6, elbow 65.5, carpus 100.9; stifle 68.2, hock 52.6 degrees (medians). Hip ROM: no value in text. | S4 text: "Shoulder ROM ... (Mdn = 26.62 degrees)", "Elbow ROM ... floor height (Mdn = 65.5 degrees)", "carpal ROM ... floor height (Mdn = 100.94 degrees)", "Stifle ROM ... floor height (Mdn = 68.16 degrees)", "Hock ROM ... floor height (Mdn = 52.62 degrees)". Marker-based, skin markers, so soft-tissue error. S1's own hock range 26-66 = 40 degrees and stifle 41-87 are of the same order. |
| Elbow/carpus pattern | elbow flexion-extension is "biphasic" in swing; the carpus bends strongly in swing (ROM ~100 degrees) | S8: "the forelimb elbow joint exhibits a biphasic flexion-extension pattern during the swing phase, followed by slight continued extension and subsequent flexion during the stance phase" (German Shepherds); S4 carpus ROM ~101 degrees. In a walk the paw is folded back at the carpus in swing and swung forward; stance carpus roughly straight with slight extension at midstance. |
| Carpus hyperextension in stance | [gap] for the walk; the trot value for German Shepherds is a carpal ROM of 29.4 degrees in stance vs 88.7 in swing (S8, via fetch summary), i.e. the stance carpus moves little compared with swing. | |
| Forelimb elevation-angle excursion | forelimb horizontal and vertical endpoint excursions are larger than the hindlimb's in all gaits | S2: "Horizontal limb excursions were significantly higher for FL than for HL in all gaits (p<0.03) ... Vertical limb excursions were also significantly higher for FL than for HL in all gaits (p<0.04)"; numbers normalised to hindlimb length are in Fig 2 which I could not read. |
| Elbow-shoulder-carpus coupling | elbow negatively correlated with shoulder and carpus through most of the cycle; shoulder and carpus positively correlated | Search-result snippet for a mixed-breed walking study (not read) |

## (c) Reach, lift, stride, body bob

| Quantity | Value | Source |
|---|---|---|
| Hind paw position at TD relative to hip | Thigh 44-52 degrees ahead of vertical and metatarsus ~+40 degrees at TD: the paw lands well ahead of the hip, roughly under the knee/stifle. As a fraction of hindlimb length: [gap] (S2 Fig 2 has it but was unreadable). | S1 Tables, Fig 1 |
| Hind paw position at TO relative to hip | Thigh vertical, tibia -55 degrees: paw trails behind the hip by roughly the length of the metatarsus plus a tibia-length times sin 55 degrees. Estimate: paw ~0.3-0.5 limb-length behind the hip [est, geometry from the angles; segment lengths assumed tibia ~ femur ~ 0.4 of limb, metatarsus ~ 0.25]. | S1 angles + my geometry |
| Foreleg stride-reach | Estimate: scapula rotates ~35 degrees; humerus swing and forearm swing about equal; forefoot reaches ~0.25-0.35 limb-length ahead of the shoulder at TD and ~0.25-0.35 behind at TO [est; no number found] | est |
| Paw lift in swing | [gap] No clearance number found in fetched text. Estimate: at a slow walk the swing paw clears the ground by ~ one paw-height to one-tenth of the limb [est]; the carpus and hock fold so the paw sits roughly at the level of the opposite carpus/hock at mid-swing (this is what Muybridge plate 704 shows, see below). | est + plate 704 |
| Stride length and frequency, slow walk | [gap] S2 Fig 1C-D, S3 Table: none in readable text. Arithmetic anchor from speeds and duty: speed 0.78-1.0 m/s; I have no verified stride length; do not use a figure from this row. | |
| Overtracking / understepping | Hind paw lands at about or slightly behind the print of the same-side fore at a slow walk [est, from the lateral-couplet pattern; Hildebrand: dogs with the hind foot landing before the fore has left cannot overtrack]. [gap] No measured value. S7: "trotting dogs instead pass both hind feet to the same side of the forefeet" (trot only: to avoid interference). | |
| Pelvis tilt | small biphasic wave, "pitch", per stride: a few degrees (Whippet 48-50 degrees, range ~2) | S1 Table 1 (pelvis rows) |
| Withers / croup vertical bob, head nod, tail at walk | [gap] none found in the sources read. Textbook estimate [est]: croup and withers each go up and down twice per stride (once per footfall pair), with the croup lowest right after a hind touchdown and highest at the midpoint of a hind stance; amplitude small (about 1-2 % of leg length at a walk; at a slow relaxed walk the bob is hard to see). Head nod: in dogs the head is held steady-ish at a walk with a slight rise-and-fall once per stride; Muybridge's Dread walks with the head low and swinging; a relaxed dog keeps the tail low with a gentle sway [est]. | est |

## (d) What an animator gets wrong (checklist)

Sourced from S1, S2, S5-S7 where marked, otherwise common animation practice [est] (Richard Williams, Animator's Survival Kit quadruped
chapter; I could not fetch it, so treat "[est]" items as recollection).

1. Legs in lockstep. A walk is a lateral sequence: all four feet touch down at different times; the two legs of a pair are 50 % of a cycle apart (S2). A pair moving together is a trot or a pace.
2. Equal timing front and back. Fore and hind contact times are equal on average (S7), but the hind pair is not "just the front pair shifted": the hind leg is strongly angled (thigh ahead of vertical at TD, shank behind) and the hock is NEVER straight.
3. Straight or rubber legs. The hind limb has three working segments and a zig-zag: stifle always bent 40-60 degrees in stance and 60-90 in swing; hock bent 25-65 degrees all through the stride (S1). A hind leg drawn straight at any moment of a walk is wrong.
4. A swing that is too symmetric. In swing the leg does not just retrace the stance path; the hock and stifle fold to their maximum at ~75-80 % of the stride and the paw trails (S1). The foot is moved forward mostly by the shank; the thigh only starts to swing forward after toe-off.
5. Paw drag/skate. Stance is ~60 % of the cycle and the paw does not slide; in the sprite the grounded paw must stay fixed relative to the ground while the body moves (S1: stance is 58-64 % of the cycle).
6. Not enough carpus fold. In swing the forearm folds up at the carpus (~100 degrees ROM, S4) and the paw hangs; in stance the foreleg is near straight. Muybridge plate 704 frames 3, 4, 8, 12 show the carried paw hanging with a bent carpus (see below).
7. Leg motion from the shoulder joint. The shoulder joint hardly moves; the whole scapula slides/rotates ~35 degrees (S5, S6). A rig that rotates a humerus-only pivot at the shoulder point looks stiff; the fore limb top should swing from a point higher up, near the withers.
8. Hip and shoulder at the same height / same pivot. The hip joint is level with the top of the shoulder joint (S5, S6), i.e. a little below the withers line.
9. Segment lengths. Humerus is 27 % of foreleg length in all breeds; scapula 24-34 % (S5).
10. A slow walk that has a suspension phase or toe-off while the other hind foot has not yet landed. Duty factor is > 0.5 at a walk (0.56-0.64, S1), so at least two feet are always down; a bounce or float is trot/amble.
11. Too much bob. [est] A slow walk has little vertical body motion; a trot-like bounce says "trot".
12. Dead head and tail. Muybridge's Dread walks with a low, swinging head and a raised, curving tail; the head and tail should move once per stride, out of phase with the legs [est]. Silhouette check: [est] the most common sign of a "wrong" 2D walk is that the contact poses (front paw far forward and hind paw far back at the same time on the same side) are not offset by about a quarter cycle.
13. Standard 4-pose breakdown for a quadruped walk [est]: contact, down (lowest), passing, up (highest) for each limb, the hind pair offset from the fore pair by about a quarter cycle on the same side and half a cycle between left and right. Use these as keys but make sure the angles above are met at contact and passing.

## (e) Images

Tracked beside this file: `muybridge_704_side_frames1-6.png` and `muybridge_704_side_frames7-12.png`, crops of the side
rows of the plate described below. Muybridge's work is public domain (published 1887; he died 1904).

### muybridge_704_dread_walking_BPL.jpg  (2766 x 2476; not in this repository)
Source: https://commons.wikimedia.org/wiki/File:Animal_locomotion._Plate_704_(Boston_Public_Library).jpg ; original upload URL
https://upload.wikimedia.org/wikipedia/commons/8/8d/Animal_locomotion._Plate_704_%28Boston_Public_Library%29.jpg. Licence: Public domain (Muybridge,
"Animal Locomotion" 1887, Plate 704 "'Dread' walking", mastiff; Boston Public Library scan). A higher-resolution scan (9580 x 7747) exists at
Commons: File:Dog Dread walking (rbm-QP301M8-1887-704).jpg (USC Digital Library, public domain), not downloaded.
Contents: 4 rows x 6 frames. Rows 1 and 3 are the side view (frames 1-6 and 7-12, one continuous walk, dog moving to the right; head and nose low, tail curling up
behind); rows 2 and 4 are rear/three-quarter views of the same 12 instants (labelled 1-6 and 7-12).
Crops of the side rows: muybridge_704_side_frames1-6.png and muybridge_704_side_frames7-12.png (crops of this plate, same licence).

Frame-by-frame, side view (dog faces right; "near" = leg on the camera side; this is a thin, long-legged mastiff, the frames are coarse and
the near/far legs overlap, so treat each line as what I can see, not an exact limb assignment):
- 1: Near fore reaches far forward and down, paw flat on the floor at the right edge, leg slanted ~30 degrees forward from vertical (touchdown/early stance). Far fore under the chest.
  A hind leg trails at the left, slanted back with the toes on the floor and heel up (toe-off). Head low, nose near the floor.
- 2: Near fore still planted well ahead, same slant, body has moved over it; hind legs gathered under the rump, one hind paw placed near the left edge.
- 3: The planted near fore is still ahead. The other fore (middle of the frame) is lifted, forearm angled forward and the paw hanging folded at the carpus under the chest. Hind legs under the hips. Tail curved up.
- 4: The lifted fore has moved forward and is still folded, paw a little above the floor, about at mid-chest depth; the planted leg is now close to vertical under the shoulder (mid-stance). A hind paw lifts on the left.
- 5: The two forelegs cross under the chest: one leg is planted and leaning back, the other is swinging through, reaching down-right so its paw is about to land well ahead of the chest. A hind leg is lifted at the left.
- 6: Reaching fore has landed at the right, planted forward; the trailing fore is behind it and leaving the floor; the far hind is carried forward under the belly, bent.
- 7: Both forefeet on the floor, close together under the chest; near hind paw lifted and tucked below the belly in the centre-left; the other hind trails at the left.
- 8: One fore is lifted and swinging forward with the paw hanging folded (right-centre); the other fore is near vertical; a hind leg trails far back at the left with the toes on the floor.
- 9: Lifted fore is carried forward and still folded; the trailing hind leg is stretched far behind (toes down, shank slanted back about 45 degrees); other hind leg under the hips.
- 10: Both fores planted (one at the right, leaning forward, one under the chest); hind legs bunched under the hips; body low-forward.
- 11: A hind paw is lifted and crosses in front of the other hind leg, close to the belly at the left-centre; fore legs crossing again at the right.
- 12: One fore lifted with the paw hanging back-and-up behind the carpus (carpus flexed ~90 degrees); a hind leg lifted with the hock sharply bent and the foot hanging; tail raised in an S curve.
Things visible in the whole strip: (1) the head is far below the withers all the time, so the neck slopes forward-down; (2) the swing limb passes right next to the stance limb so the legs cross; (3) the lifted paw hangs folded at the carpus and the hock, and is raised only a short way off the floor; (4) the hind feet land about under the hip/stifle, the tail swings.
This is one dog, a low-headed, ageing-looking lean mastiff, not a standard-posture dog; use it for sequence and fold, not for proportions or head carriage.

## (f) Where sources disagree, and the gaps

- Duty factor depends on the speed in the same study: walk 0.56-0.64 between the fluoroscopy and the marker session of the SAME dogs (e.g. Malinois 0.58 vs 0.64, Whippet 0.60 vs 0.56). Use ~0.6 as the working value, not a precise figure (S1).
- S1's text on when the stifle and hock flex ("in the last quarter of the swing phase", "continues for about the first two thirds of the stance phase") reads opposite to its plotted curves in places; I used the plotted numbers and flagged it above.
- Sign convention: S1's caption says positive = flexion for joints but prints negative values for hip/stifle; I treated magnitude as bend away from straight, checked against segment-angle subtraction for the stifle and hock (they agree within ~5 degrees).
- Marker data vs X-ray differ substantially for the femur and for the pelvis (S1: "deviate significantly in the amplitudes and timing"); the hock and metatarsus curves in Figs 1-2 exist only as marker data.
- The Muybridge plate number: Wellcome and Commons say Plate 704 is "'Dread' walking"; a dealer lists 703 as "Dog; walking; interrupted" with the same dog; the NGA record for 706 is titled trotting but its description says walking (search results). Dread is a mastiff, not a medium dog.
- Not found (did not estimate except where marked [est]): forelimb shoulder/elbow/carpus angles at TD/mid-stance/TO/mid-swing; fore paw reach and lift in units of leg length; hind paw lift; the fore-hind same-side phase lag as a number; stride length and frequency at a slow walk relative to withers height; withers/croup bob amplitudes; head nod; over-tracking measurements; the carpus hyperextension in a walk stance. Likely places: Fischer & Lilje 2011 "Dogs in Motion" (book, VDH), Andrada et al. 2017 Am J Vet Res 78:804 (Beagle forelimb, walk and trot), Maes et al. 2008 J Exp Biol 211:138 (Malinois, walk to gallop, speeds 0.4-10 m/s; abstract only seen), Hildebrand 1968 Symmetrical gaits of dogs in relation to body build (J Morphol / full text blocked), Catavitello 2015 Figs 1-3 (the PLoS figures themselves, which were not downloaded).

## Speed comparison (brief)

| Gait | Footfalls | Duty factor | Source |
|---|---|---|---|
| Slow/normal walk | lateral sequence, 3 feet down most of the time, no suspension | 0.56-0.64 | S1, S2 |
| Fast walk | still lateral sequence; stance shortens toward 0.55; same-side hind and fore pair closer ("lateral couplets") | ~0.55-0.58 (Malinois 1.3 m/s: 0.58) | S1, S7 |
| Amble / pace | not a lateral sequence; Hildebrand: only some long-legged dogs pace; "Animals that pace (camelids, certain horses and dogs) are all long-legged"; "usually pace and trot no faster than a slow run" (S7); pace forefoot contact 99-116 % of hind (S7) | [gap] | S7 |
| Trot | diagonal pairs together (RH+LF, LH+RF); fore swing 41 %, hind swing 49 % of the cycle (German Shepherds, S8); feet of a diagonal pair land together; suspension phase between pairs; rearward limb motion < 50 % of the cycle (S2) | 0.41-0.47 (Whippet 0.42, Malinois 0.42, Beagle 0.42, Fr. Bulldog 0.47; marker 0.41-0.42) | S1, S2, S8 |
| Gallop | asymmetrical, 1 foot lead; contralateral phase lag 18 % (fore) / 26 % (hind) instead of 50 % | | S2 |

## What a walk sheet must pass

A trial walk is a sheet of frames of the standing sprite with moving legs. It is accepted only when:

1. Every cell of the standing sprite's head, collar, back, chest and tail is the same in every frame (one row lower in
   the frames in which the body sinks).
2. No colour outside the dog's 14 is used.
3. No sliding: a near paw that is on the sand (white toes in rows 73 to 75) is, in the next frame, either off the sand
   or exactly one step of the body's advance farther back, so it stays on one spot while the body moves forward. The
   same for the far paws (cream toes in rows 70 to 72). Control: with a wrong step this check must fail.

A walk that was tried (a fifth leg model) failed at the joins of leg and body, and its code was deleted: start again
from this file.
