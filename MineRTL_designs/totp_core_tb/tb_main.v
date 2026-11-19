`timescale 1ns/1ps
module tb_main;
    reg clk = 0;
    reg rst = 1;
    reg start = 0;
    reg [31:0] counter;
    wire [19:0] code;
    wire done;

    main dut(.clk(clk), .rst(rst), .start(start), .counter(counter), .code(code), .done(done));

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
            end else begin
                $display("PASS counter=%0d code=%0d", ctr, code);
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
