// HMAC-SHA1 TOTP core, key baked in (RFC 4226/6238 test key "12345678901234567890").
// Only variable input is the 32-bit time-step counter. Two SHA-1 compressions
// (inner: S_in + block(counter), outer: S_out + block(H)) then truncate/mod 10^6.
// Mirrors ref.py/datapath.py/netlist.py's already RFC-vector-verified design.
//
// Two optimizations over the first working version (see README.md "Optimizing it"):
//   1. No separate `block_mem` register -- for the first 16 rounds, `sched` is a pure
//      rotation of the initial block words, so `sched[0]` already equals what
//      `block_mem[round]` used to hold. Saves 512 flip-flops (16 words x 32 bits).
//   2. `e + K[round] + w` for the NEXT round is computed and registered one cycle
//      ahead (into `ekw_reg`), so each round's critical add is just
//      `rol5(a) + f + ekw_reg` (2 levels) instead of `rol5(a) + f + e + K + w`
//      (4 sequential 32-bit adds) -- this is the classic SHA-1 round-pipelining trick.
module main(
    input clk,
    input rst,
    input start,
    input [31:0] counter,
    output [19:0] code,
    output done
);
    // S_in = compress(IV, key^ipad), S_out = compress(IV, key^opad) for the RFC test key.
    localparam [31:0] SIN0 = 32'hcbc80c8c, SIN1 = 32'hf599e2ac, SIN2 = 32'hbdb8c832,
                       SIN3 = 32'hda95c1c3, SIN4 = 32'hf8683025;
    localparam [31:0] SOUT0 = 32'h98bdbdcd, SOUT1 = 32'h58e07bfe, SOUT2 = 32'had5cddea,
                       SOUT3 = 32'h3ac0430b, SOUT4 = 32'hfe106825;

    localparam IDLE=0, LOAD1=1, RUN1=2, FF1=3, LOAD2=4, RUN2=5, FF2=6, TRUNC=7, DONE=8;
    reg [3:0] state;
    reg [6:0] round;

    reg [31:0] a, b, c, d, e;
    reg [31:0] sched [0:15];
    reg [31:0] ekw_reg; // e + K[round] + w for the CURRENT round, computed last cycle
    reg [31:0] h0, h1, h2, h3, h4;   // saved after first feed-forward
    reg [31:0] dg0, dg1, dg2, dg3, dg4; // final digest words (big-endian H0..H4)
    reg [19:0] code_r;
    reg done_r;

    function [31:0] rol;
        input [31:0] x;
        input [4:0] n;
        begin
            rol = (x << n) | (x >> (32 - n));
        end
    endfunction

    function [31:0] f_fn;
        input [31:0] bb, cc, dd;
        input [6:0] t;
        begin
            if (t < 20)
                f_fn = (bb & cc) | ((~bb) & dd);
            else if (t < 40)
                f_fn = bb ^ cc ^ dd;
            else if (t < 60)
                f_fn = (bb & cc) | (bb & dd) | (cc & dd);
            else
                f_fn = bb ^ cc ^ dd;
        end
    endfunction

    function [31:0] k_fn;
        input [6:0] t;
        begin
            if (t < 20) k_fn = 32'h5A827999;
            else if (t < 40) k_fn = 32'h6ED9EBA1;
            else if (t < 60) k_fn = 32'h8F1BBCDC;
            else k_fn = 32'hCA62C1D6;
        end
    endfunction

    // This round's work: only 2 sequential adds on the critical path.
    wire [31:0] w_cur = (round < 16) ? sched[0]
                       : rol(sched[13] ^ sched[8] ^ sched[2] ^ sched[0], 1);
    wire [31:0] f_cur = f_fn(b, c, d, round);
    wire [31:0] sum_cur = rol(a, 5) + f_cur + ekw_reg;

    // Next round's e + K + w, computed now (in parallel with sum_cur, off the
    // critical path) and registered for next cycle's use. next_e is just d
    // (the value e will hold next cycle); next_w looks at what `sched` will
    // be AFTER this cycle's shift -- sched[i+1] for i<=14, so it only ever
    // reads indices 1,3,9,14 of the CURRENT (pre-shift) sched.
    wire [6:0] next_round = round + 1;
    wire [31:0] next_w = (next_round < 16) ? sched[1]
                        : rol(sched[14] ^ sched[9] ^ sched[3] ^ sched[1], 1);
    wire [31:0] next_ekw = d + k_fn(next_round) + next_w;

    wire [159:0] digest_bytes = {dg0, dg1, dg2, dg3, dg4};
    wire [3:0] off = dg4[3:0];
    wire [31:0] trunc_v = digest_bytes[(159 - 8*off) -: 32];
    wire [31:0] trunc_masked = {1'b0, trunc_v[30:0]};

    integer i;
    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            done_r <= 0;
        end else begin
            case (state)
                IDLE: begin
                    done_r <= 0;
                    if (start) state <= LOAD1;
                end
                LOAD1: begin
                    sched[0] <= 32'h0;
                    sched[1] <= counter;
                    sched[2] <= 32'h80000000;
                    for (i = 3; i < 15; i = i + 1) sched[i] <= 32'h0;
                    sched[15] <= 32'h240;
                    a <= SIN0; b <= SIN1; c <= SIN2; d <= SIN3; e <= SIN4;
                    // round 0's e+K+w: e=SIN4, K[0], w0=block[0]=0 (known directly,
                    // same as sched[0] above).
                    ekw_reg <= SIN4 + k_fn(0) + 32'h0;
                    round <= 0;
                    state <= RUN1;
                end
                RUN1: begin
                    e <= d; d <= c; c <= rol(b, 30); b <= a; a <= sum_cur;
                    for (i = 0; i < 15; i = i + 1) sched[i] <= sched[i+1];
                    sched[15] <= w_cur;
                    ekw_reg <= next_ekw;
                    if (round == 79) state <= FF1;
                    round <= round + 1;
                end
                FF1: begin
                    h0 <= a + SIN0; h1 <= b + SIN1; h2 <= c + SIN2; h3 <= d + SIN3; h4 <= e + SIN4;
                    state <= LOAD2;
                end
                LOAD2: begin
                    sched[0] <= h0; sched[1] <= h1; sched[2] <= h2;
                    sched[3] <= h3; sched[4] <= h4; sched[5] <= 32'h80000000;
                    for (i = 6; i < 15; i = i + 1) sched[i] <= 32'h0;
                    sched[15] <= 32'h2A0;
                    a <= SOUT0; b <= SOUT1; c <= SOUT2; d <= SOUT3; e <= SOUT4;
                    // round 0's e+K+w for pass 2: e=SOUT4, K[0], w0=block[0]=h0.
                    ekw_reg <= SOUT4 + k_fn(0) + h0;
                    round <= 0;
                    state <= RUN2;
                end
                RUN2: begin
                    e <= d; d <= c; c <= rol(b, 30); b <= a; a <= sum_cur;
                    for (i = 0; i < 15; i = i + 1) sched[i] <= sched[i+1];
                    sched[15] <= w_cur;
                    ekw_reg <= next_ekw;
                    if (round == 79) state <= FF2;
                    round <= round + 1;
                end
                FF2: begin
                    dg0 <= a + SOUT0; dg1 <= b + SOUT1; dg2 <= c + SOUT2; dg3 <= d + SOUT3; dg4 <= e + SOUT4;
                    state <= TRUNC;
                end
                TRUNC: begin
                    code_r <= trunc_masked % 1000000;
                    done_r <= 1;
                    state <= DONE;
                end
                DONE: begin
                    if (!start) state <= IDLE;
                end
            endcase
        end
    end

    assign code = code_r;
    assign done = done_r;
endmodule
