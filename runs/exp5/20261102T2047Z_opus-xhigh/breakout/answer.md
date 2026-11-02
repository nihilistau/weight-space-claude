## Design

**Strategy.** The policy predicts the column where the ball will reach row 8, which is the row just above the paddle. It then moves the paddle toward that column and waits there.

The ball's horizontal motion, including the side-wall "clamp and flip", is a fold of an unfolded coordinate u:
- fold(u) = m if m ≤ 9, otherwise 19 − m, where m = u mod 20.

The landing column is then T = fold(x + h·N), where:
- h is the effective horizontal direction (+1 right, −1 left).
- N is the number of steps until the ball reaches row 8.
  - Descending ball: N = 8 − y.
  - Ascending ball: assume it bounces off a brick row so it sits at row s = min(3, y). That gives N = y + 9 − 2s.

Once the ball is descending, the prediction is exact. At row 8 the target is the ball's own column, so the catch always reflects the ball straight back up (the "ball_x == pos" case). This keeps the trail-based direction reading correct after the bounce.

**Direction from the trail** (ball cell versus trail cell, both one-hot):
- **h (horizontal):** h = +1 when bx − tx = 1, or when the ball sits still at column 0 (bx = tx = 0). Otherwise h = −1, which covers the wall-stay at column 9 and the start states.
- **v (vertical):** "down" when the trail is above the ball. It is also "down" when the trail is in the same row and the ball is at row ≤ 4, which covers brick hits and the top-wall bounce. It is "up" when the trail is below the ball, or when ball and trail are both in row 8 (just after a paddle bounce).

**Hidden layer 1 (6 units used):**
- **u0 = Hr:** ±1, "moving right".
  - Ball weight is 8·col, with column 0 set to 8; trail weight is −8·col; bias −4.
- **u1 = Vd:** ±1, "moving down".
  - Ball weight is 8·a(row), with a(r) = r + 0.5 for rows 0–7 and a(8) = 7.5; trail weight is −8·row.
- **u2–u5 = S_d** for the four direction classes (h+ down, h− down, h+ up, h− up):
  - S_d = tanh(4·(T_d(ball cell) − paddle column)), which gives −1, 0 or +1.
  - T_d is a 100-entry lookup table over the ball cell.

**Hidden layer 2 (8 units):** each unit is a 3-way AND, tanh(3·(±Hr ± Vd ± 2·S_d − 3)).
- R_d (units 0–3) is +1 only when class d is active and the target is to the right.
- L_d (units 4–7) is the same with the target to the left.

**Output layer.**
- right logit = 10·ΣR + 30, which is about +10 when a right move is wanted and about −10 otherwise.
- left logit is built the same way from the L units.
- noop, up, down and fire all stay at 0, so the paddle holds still when it is under the target.

```edits
# u0 = Hr (moving right): ball columns
W1[3:600:60, 0] = 8
W1[9:600:60, 0] = 8
W1[15:600:60, 0] = 16
W1[21:600:60, 0] = 24
W1[27:600:60, 0] = 32
W1[33:600:60, 0] = 40
W1[39:600:60, 0] = 48
W1[45:600:60, 0] = 56
W1[51:600:60, 0] = 64
W1[57:600:60, 0] = 72
# trail columns
W1[10:600:60, 0] = -8
W1[16:600:60, 0] = -16
W1[22:600:60, 0] = -24
W1[28:600:60, 0] = -32
W1[34:600:60, 0] = -40
W1[40:600:60, 0] = -48
W1[46:600:60, 0] = -56
W1[52:600:60, 0] = -64
W1[58:600:60, 0] = -72
b1[0] = -4
# u1 = Vd (moving down): ball rows
W1[3:60:6, 1] = 4
W1[63:120:6, 1] = 12
W1[123:180:6, 1] = 20
W1[183:240:6, 1] = 28
W1[243:300:6, 1] = 36
W1[303:360:6, 1] = 44
W1[363:420:6, 1] = 52
W1[423:480:6, 1] = 60
W1[483:540:6, 1] = 60
W1[543:600:6, 1] = 76
# trail rows
W1[64:120:6, 1] = -8
W1[124:180:6, 1] = -16
W1[184:240:6, 1] = -24
W1[244:300:6, 1] = -32
W1[304:360:6, 1] = -40
W1[364:420:6, 1] = -48
W1[424:480:6, 1] = -56
W1[484:540:6, 1] = -64
W1[544:600:6, 1] = -72
# u2 = S for class (right, down): landing table
W1[3:600:6, 2] = [8,9,9,8,7,6,5,4,3,2,
  7,8,9,9,8,7,6,5,4,3,
  6,7,8,9,9,8,7,6,5,4,
  5,6,7,8,9,9,8,7,6,5,
  4,5,6,7,8,9,9,8,7,6,
  3,4,5,6,7,8,9,9,8,7,
  2,3,4,5,6,7,8,9,9,8,
  1,2,3,4,5,6,7,8,9,9,
  0,1,2,3,4,5,6,7,8,9,
  0,1,2,3,4,5,6,7,8,9]
# u3 = S for class (left, down)
W1[3:600:6, 3] = [7,6,5,4,3,2,1,0,0,1,
  6,5,4,3,2,1,0,0,1,2,
  5,4,3,2,1,0,0,1,2,3,
  4,3,2,1,0,0,1,2,3,4,
  3,2,1,0,0,1,2,3,4,5,
  2,1,0,0,1,2,3,4,5,6,
  1,0,0,1,2,3,4,5,6,7,
  0,0,1,2,3,4,5,6,7,8,
  0,1,2,3,4,5,6,7,8,9,
  0,1,2,3,4,5,6,7,8,9]
# u4 = S for class (right, up)
W1[3:600:6, 4] = [9,9,8,7,6,5,4,3,2,1,
  8,9,9,8,7,6,5,4,3,2,
  7,8,9,9,8,7,6,5,4,3,
  6,7,8,9,9,8,7,6,5,4,
  7,8,9,9,8,7,6,5,4,3,
  8,9,9,8,7,6,5,4,3,2,
  9,9,8,7,6,5,4,3,2,1,
  9,8,7,6,5,4,3,2,1,0,
  8,7,6,5,4,3,2,1,0,0,
  0,1,2,3,4,5,6,7,8,9]
# u5 = S for class (left, up)
W1[3:600:6, 5] = [8,7,6,5,4,3,2,1,0,0,
  7,6,5,4,3,2,1,0,0,1,
  6,5,4,3,2,1,0,0,1,2,
  5,4,3,2,1,0,0,1,2,3,
  6,5,4,3,2,1,0,0,1,2,
  7,6,5,4,3,2,1,0,0,1,
  8,7,6,5,4,3,2,1,0,0,
  9,8,7,6,5,4,3,2,1,0,
  9,9,8,7,6,5,4,3,2,1,
  0,1,2,3,4,5,6,7,8,9]
# scale tables by K=4
W1[3:600:6, 2] *= 4
W1[3:600:6, 3] *= 4
W1[3:600:6, 4] *= 4
W1[3:600:6, 5] *= 4
# paddle column (row 9, channel 0) subtracts 4*col
W1[540:600:6, 2] = [0, -4, -8, -12, -16, -20, -24, -28, -32, -36]
W1[540:600:6, 3] = [0, -4, -8, -12, -16, -20, -24, -28, -32, -36]
W1[540:600:6, 4] = [0, -4, -8, -12, -16, -20, -24, -28, -32, -36]
W1[540:600:6, 5] = [0, -4, -8, -12, -16, -20, -24, -28, -32, -36]
# layer 2: R units 0-3 (go right), L units 4-7 (go left)
W2[0, 0] = 3
W2[1, 0] = 3
W2[2, 0] = 6
W2[0, 1] = -3
W2[1, 1] = 3
W2[3, 1] = 6
W2[0, 2] = 3
W2[1, 2] = -3
W2[4, 2] = 6
W2[0, 3] = -3
W2[1, 3] = -3
W2[5, 3] = 6
W2[0, 4] = 3
W2[1, 4] = 3
W2[2, 4] = -6
W2[0, 5] = -3
W2[1, 5] = 3
W2[3, 5] = -6
W2[0, 6] = 3
W2[1, 6] = -3
W2[4, 6] = -6
W2[0, 7] = -3
W2[1, 7] = -3
W2[5, 7] = -6
b2[0:8] = -9
# outputs: right = action 3, left = action 1
W3[0:4, 3] = 10
W3[4:8, 1] = 10
b3[3] = 30
b3[1] = 30
```