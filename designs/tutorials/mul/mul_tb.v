/*
	Digital ASIC Development, The Open Source Way
	Tutorial 2: RTL Verification — self-checking testbench for mul.v

	Follows the rules in the tutorial's "Writing a Self-Checking Verilog
	Testbench" section:
	  - a reference model computes the expected result (here: Verilog's own *)
	  - comparison uses case equality (!==) so X/Z is never silently ignored
	  - the first mismatch stops the run with $fatal(1)  -> vvp exit status 1
	  - every message carries enough context to reproduce the failure
*/
`timescale 1ns/1ps

module mul_tb;

	reg  signed  [7:0] mp, mc;	// Registers to drive the DUV inputs
	wire signed [15:0] p;		// Wires to observe the DUV outputs

	integer tests_run = 0;

	mul DUV ( .mp(mp), .mc(mc), .p(p) );

	initial begin
	    $dumpfile("mul.vcd");	// vcd dump file
	    $dumpvars;				// dump every variable in the whole design
	end

	// Self-checking task: drive one pair, compare against the reference model.
	task automatic check_mul(input signed [7:0] a, input signed [7:0] b);
		reg signed [15:0] exp;
		begin
			exp = a * b;			// reference model
			mp  = a;
			mc  = b;
			#1;						// allow combinational propagation

			if (p !== exp) begin
				$display("ERROR: mp=%0d mc=%0d expected=%0d got=%0d", a, b, exp, p);
				$fatal(1);
			end
			tests_run = tests_run + 1;
			$display("  ok: %0d x %0d = %0d", a, b, p);
		end
	endtask

	initial begin
		mp = 8'd0;
		mc = 8'd0;

		// the three cases from the original testbench
		check_mul( 8'd10,  8'd20);	// positive x positive
		check_mul( 8'd20,  8'd20);
		check_mul( 8'd20, -8'd5 );	// positive x negative

		// edge cases the original testbench never reached
		check_mul(-8'd128, -8'd128);	// most-negative x most-negative
		check_mul(-8'd128,  8'd1  );	// |-128| does not fit in 8 signed bits
		check_mul( 8'd127,  8'd127);	// largest magnitude positive product
		check_mul( 8'd0,   -8'd128);	// zero with a negative operand

		$display("PASS: %0d/%0d tests passed", tests_run, tests_run);
		$finish;
	end

endmodule
