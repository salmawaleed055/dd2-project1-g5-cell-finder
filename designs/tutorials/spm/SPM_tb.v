// Tutorial 4 - self-checking testbench for SPM.
//
// The same file runs in three modes, unmodified:
//   RTL                iverilog -o spm_rtl SPM_tb.v SPM.v CSADD.v TCMP.v
//   unit-delay GLS     iverilog -o spm_gl  SPM_tb.v SPM.mapped.gl.v pdk/verilog/sky130_fd_sc_hd.v
//   SDF-annotated GLS  iverilog -gspecify -DSKY130_FD_SC_HD__LPFLOW_BLEEDER_1_V \
//                        -DUSE_SDF -o spm_sdf SPM_tb.v SPM.mapped.gl.v \
//                        pdk/verilog/primitives.v pdk/verilog/sky130_fd_sc_hd.v
//
// The timing numbers below are the ones in SPM.sdc. A testbench that applies
// stimulus earlier than set_input_delay promised, or samples later than
// set_output_delay promised, is not testing the circuit that STA signed off.
// Override them from the command line, e.g.  iverilog -DTCLK=1.5625 ...

`timescale 1ns/1ps

`ifndef TCLK
  `define TCLK 1.25          // create_clock -period
`endif
`ifndef TIN
  `define TIN  0.40          // set_input_delay
`endif
`ifndef TOUT
  `define TOUT 0.40          // set_output_delay
`endif
`ifndef SDF_FILE
  `define SDF_FILE "SPM.cells.sdf"
`endif

module SPM_tb;
    localparam SIZE = 32;
    localparam real TCLK = `TCLK;
    localparam real TIN  = `TIN;
    localparam real TOUT = `TOUT;

    reg clk = 0, rst = 1, y = 0;
    reg signed [SIZE-1:0] X = 0;
    wire p;
    reg signed [63:0] prod;
    reg signed [63:0] exp;
    integer i, errors;

    SPM duv (.clk(clk), .rst(rst), .X(X), .y(y), .p(p));  // no parameter override: a netlist has no parameters

    always #(TCLK/2.0) clk = ~clk;

`ifdef USE_SDF
    initial $sdf_annotate(`SDF_FILE, duv);
`endif

    task automatic mult(input signed [SIZE-1:0] a, input signed [SIZE-1:0] b);
        begin
            rst = 1; y = 0;
            repeat (2) @(posedge clk);
            #TIN rst = 0;                 // released TIN after an edge, like any other input
            X = a; prod = 0;
            y = b[0];                     // first serial bit, in place before the first active edge

            // One iteration = one clock period, anchored on the active edge:
            //   * inputs are driven TIN  after  the edge  (set_input_delay)
            //   * p is sampled     TOUT before the next edge (set_output_delay)
            // Never drive or sample *at* the edge: RTL and the UDP-based gate
            // models resolve that race differently. See section 7.1.
            //
            // The edge that ends cycle i captures the product bit for the y bit
            // applied during cycle i -- SPM's one cycle of output latency. So
            // iteration i drives b[i] for the next cycle and reads bit i-1.
            for (i = 1; i <= 64; i = i + 1) begin
                @(posedge clk);
                #TIN;
                y = (i < 64) ? ((i < SIZE) ? b[i] : b[SIZE-1]) : 1'b0;  // LSB first, sign-extended
                #(TCLK - TIN - TOUT);
                prod[i-1] = p;
            end

            exp = a * b;
            if (prod !== exp) begin
                $display("ERROR: %0d x %0d expected=%0d got=%0d", a, b, exp, prod);
                errors = errors + 1;
            end else
                $display("  ok: %0d x %0d = %0d", a, b, prod);
        end
    endtask

    initial begin
        $dumpfile("spm.vcd"); $dumpvars;
        $display("SPM_tb: TCLK=%0.4f ns (%0.1f MHz)  TIN=%0.2f ns  TOUT=%0.2f ns",
                 TCLK, 1000.0/TCLK, TIN, TOUT);
        errors = 0;
        mult(3, 5);
        mult(-7, 9);
        mult(12345, -6789);
        mult(-2, -3);
        mult(0, 1234);
        mult(32'sh7FFFFFFF, 2);
        if (errors == 0) $display("PASS: SPM behaves as a signed 32x32 multiplier");
        else begin $display("FAIL: %0d errors", errors); $fatal(1); end
        $finish;
    end
endmodule
