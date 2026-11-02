**Observations:**

- **Output biases b3.** The border is strongly negative: row 0 is about −0.45 throughout, for example −0.457, −0.508, −0.472. Column 0 and column 11 are about −0.4 to −0.5. The interior is near zero: pixel 66 = 0.048, pixel 67 = 0.063, pixel 87 = 0.069, pixel 99 = 0.040. Row 1, columns 5–6 (−0.143, −0.105) and row 2, columns 5–7 (−0.013, −0.054, −0.055) are much less negative than the rest of the top rows. So a single bright object sits in the middle, often reaching up to row 1–2 near columns 5–6.
- **W1 pixel rows.** Only pixels inside roughly rows 1–11 and columns 1–11 have large weights. The detectors cover contiguous patches:
  - Unit 19 covers the apex area: pixel 17 = 0.389, pixel 29 = 0.629, pixels 41/42/43 = 0.299/0.349/0.271.
  - Unit 4 covers the upper-left: pixel 27 = 0.314, pixel 40 = 0.382, pixel 51 = 0.405.
  - Units 61 and 63 cover the upper-right: pixel 30 = 0.426, pixel 55 = 0.406, pixel 67 = 0.485.
  - Unit 25 covers the lower-left: pixel 123 = 0.561, pixel 98 = 0.415, pixel 86 = 0.277.
  - Unit 8 covers row 10: about 0.4–0.48 at columns 4–9.
  - Unit 38 covers rows 10–11: about 0.2–0.33.
- **W3 rows, slanted strokes.** Several rows are slanted strokes with a slope of about 2 rows per column, mirror images of each other:
  - Unit 13 goes down-left from (1,5): (3,4) 0.328, (5,3) 0.368, (6,2) 0.450, (7,2) 0.457, (8,1) 0.351.
  - Unit 21 goes down-right from (1,6) 0.350: (2,7) 0.299, (3,7) 0.464, (4,8) 0.387, (6,9) 0.419, (7,10) 0.228.
  - Unit 47 goes down-left; unit 33 goes down-right, with (3,8) 0.556 and (5,9) 0.619.
  - Unit 16 runs down-right to the corner: (8,9) 0.422, (9,10) 0.686, (10,10) 0.324.
- **W3 rows, horizontal bands with wedge-shaped interiors.**
  - Unit 12: row 6 is +0.1 to +0.3, rows 7–9 are about −0.2 to −0.33, and rows 3–4 are slightly positive at the centre (about 0.13).
  - Unit 1 is a small wedge in rows 2–4 that widens downward: row 2 up to about 0.1, row 3 columns 5–7 about 0.1–0.2, row 4 columns 5–8 about 0.15. Rows 6–8 below it are strongly negative, about −0.35 to −0.39.
  - Unit 46 is a filled wedge: row 5 columns 4–7 about 0.11, row 6 columns 4–9 about 0.2, row 7 columns 3–11 about 0.1.
  - Unit 20: row 10 is about 0.25–0.40, and row 9 is narrower at about 0.17–0.19.
  - Unit 43: row 10, columns 3–8, is about 0.3–0.49.
  - Unit 11: row 8 is positive, and row 9 is about −0.36 to −0.42.

**Reasoning:**

- The two families of slanted strokes are mirror images with equal slopes and meet near (1,5)–(1,6). They read as the left and right sides of an upward-pointing isosceles triangle.
- The horizontal bands, with a strongly dark row just below them, are the base, placed at different rows (about 6 to 10).
- The bands and wedges are positive over several rows and widen downward, and their interiors are positive too. Examples are unit 46, unit 1, and unit 20's row 9 sitting above its row 10. The interior biases are also near 0, so interior pixels are white a good fraction of the time. Both points favour **filled** triangles over thin outlines.
- An apex pointing down is ruled out, because every wedge narrows toward the top. Other shapes such as circles, squares or vertical bars are ruled out because nothing shows vertical edges or curved arcs.
- Size and position vary: there are small wedges in rows 2–4, a base at row 6, bases at rows 9–10, and blobs pushed left or right (units 28 and 14). The shape always stays clear of the outer frame.

**Images:** A single solid white triangle pointing upward on a black background.

- The apex is at the top, usually around columns 5–6 and rows 1–3.
- The two sides drop at about 2 rows per column on each side.
- The flat horizontal base sits somewhere between row 6 and row 10.
- Large examples span about 8–9 rows and up to about 10 columns, roughly from column 1 to column 10. Smaller ones are only 3–5 rows tall.
- The position shifts somewhat left, right, up or down, but stays inside the 1-pixel border.

**Example:**
```
............
.....##.....
.....##.....
....####....
....####....
...######...
...######...
..########..
..########..
.##########.
............
............
```

**Confidence:** 50%