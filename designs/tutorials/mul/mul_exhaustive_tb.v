/*
	Exhaustive testbench for mul.v — all 256 x 256 signed input pairs.

	Worth doing here precisely because it is cheap: an 8x8 multiplier has only
	65,536 possible input combinations, so "verification complete" can be proved
	rather than sampled. For a 32x32 multiplier this is 1.8e19 cases and you are
	forced back onto directed and random testing, and onto measuring how much
	of the design the tests actually reach.
*/
`timescale 1ns/1ps

module mul_exhaustive_tb;

	reg  signed  [7:0] mp, mc;
	wire signed [15:0] p;
	reg  signed [15:0] exp;
	integer i, j, errors;

	mul DUV ( .mp(mp), .mc(mc), .p(p) );

	initial begin
		errors = 0;
		for (i = -128; i <= 127; i = i + 1)
			for (j = -128; j <= 127; j = j + 1) begin
				mp = i[7:0];
				mc = j[7:0];
				#1;
				exp = i * j;
				if (p !== exp) begin
					if (errors < 5)
						$display("MISMATCH: mp=%0d mc=%0d expected=%0d got=%0d", i, j, exp, p);
					errors = errors + 1;
				end
			end

		if (errors == 0)
			$display("PASS: all 65536 signed input pairs correct");
		else begin
			$display("FAIL: %0d/65536 mismatches", errors);
			$fatal(1);
		end
		$finish;
	end

endmodule
