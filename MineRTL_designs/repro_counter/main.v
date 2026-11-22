// Minimal reproducer for the live-vs-headless mystery: same clk/rst/start/done
// interface shape and the same sticky-DONE FSM pattern as totp_core/main.v
// (DONE holds until !start, exactly like the real core), but counts to a known
// small N instead of running SHA-1. If this finishes correctly and quickly in
// BOTH mchprs_headless and the live /load -c + /lever path, the live-specific
// bottleneck is proportional to real circuit size/ticks, not a functional bug.
// If it finishes in headless but not live, the bug is in the live tick/lever
// path itself, independent of circuit size.
module main (
    input clk,
    input rst,
    input start,
    output done
);
    localparam IDLE = 0, RUN = 1, DONE = 2;
    localparam N = 16'd40000; // same order of magnitude as totp_core's real critical path

    reg [1:0] state;
    reg [15:0] cnt;

    always @(posedge clk) begin
        if (rst) begin
            state <= IDLE;
            cnt <= 16'd0;
        end else begin
            case (state)
                IDLE: if (start) begin
                    state <= RUN;
                    cnt <= 16'd0;
                end
                RUN: begin
                    if (cnt == N - 1)
                        state <= DONE;
                    else
                        cnt <= cnt + 16'd1;
                end
                DONE: if (!start) state <= IDLE;
                default: state <= IDLE;
            endcase
        end
    end

    assign done = (state == DONE);
endmodule
