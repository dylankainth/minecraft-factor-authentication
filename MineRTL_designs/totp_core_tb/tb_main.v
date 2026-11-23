`timescale 1ns/1ps
module tb_main;
    reg clk = 0;
    reg rst = 1;
    reg start = 0;
    reg [31:0] counter;
    wire [19:0] code;
    wire done;
    wire [6:0] seg0, seg1, seg2, seg3, seg4, seg5;

    main dut(.clk(clk), .rst(rst), .start(start), .counter(counter), .code(code), .done(done),
              .seg0(seg0), .seg1(seg1), .seg2(seg2), .seg3(seg3), .seg4(seg4), .seg5(seg5));

    function [6:0] expected_seg;
        input [3:0] d;
        begin
            case (d)
                4'd0: expected_seg = 7'b1111110;
                4'd1: expected_seg = 7'b0110000;
                4'd2: expected_seg = 7'b1101101;
                4'd3: expected_seg = 7'b1111001;
                4'd4: expected_seg = 7'b0110011;
                4'd5: expected_seg = 7'b1011011;
                4'd6: expected_seg = 7'b1011111;
                4'd7: expected_seg = 7'b1110000;
                4'd8: expected_seg = 7'b1111111;
                4'd9: expected_seg = 7'b1111011;
                default: expected_seg = 7'b0000000;
            endcase
        end
    endfunction

    always #5 clk = ~clk;

    integer rfc10 [0:9];
    integer i;
    integer fails;

    task run_one(input [31:0] ctr, input integer expect_code);
        begin
            counter = ctr;
            start = 1;
            @(posedge clk);
            @(posedge clk); // past LOAD1
            start = 0;
            wait (done == 1);
            @(posedge clk);
            if (code !== expect_code) begin
                $display("FAIL counter=%0d expected=%0d got=%0d", ctr, expect_code, code);
                fails = fails + 1;
            end else if (seg0 !== expected_seg(expect_code % 10) ||
                         seg1 !== expected_seg((expect_code / 10) % 10) ||
                         seg2 !== expected_seg((expect_code / 100) % 10) ||
                         seg3 !== expected_seg((expect_code / 1000) % 10) ||
                         seg4 !== expected_seg((expect_code / 10000) % 10) ||
                         seg5 !== expected_seg((expect_code / 100000) % 10)) begin
                $display("FAIL counter=%0d code=%0d but seven-seg digits wrong: seg5..0=%b %b %b %b %b %b",
                         ctr, code, seg5, seg4, seg3, seg2, seg1, seg0);
                fails = fails + 1;
            end else begin
                $display("PASS counter=%0d code=%0d seg5..0=%b %b %b %b %b %b", ctr, code, seg5, seg4, seg3, seg2, seg1, seg0);
            end
            // wait until FSM returns to IDLE before next run
            @(posedge clk);
            @(posedge clk);
        end
    endtask

    initial begin
        rfc10[0]=755224; rfc10[1]=287082; rfc10[2]=359152; rfc10[3]=969429; rfc10[4]=338314;
        rfc10[5]=254676; rfc10[6]=287922; rfc10[7]=162583; rfc10[8]=399871; rfc10[9]=520489;
        fails = 0;
        @(posedge clk); @(posedge clk);
        rst = 0;
        @(posedge clk);
        for (i = 0; i < 10; i = i + 1) begin
            run_one(i, rfc10[i]);
        end
        if (fails == 0) $display("ALL RFC VECTORS PASSED");
        else $display("%0d FAILURES", fails);
        $finish;
    end
endmodule
