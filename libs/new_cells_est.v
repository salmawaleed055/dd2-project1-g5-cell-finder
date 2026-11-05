// Behavioural models of the new cells, generated from their Liberty functions.
module dd2_g5__f000b_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(C|(D|(~A&B)));
endmodule
module dd2_g5__f0ee0_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(~((A|B)&((C|D)&(~C|~D))));
endmodule
module dd2_g5__f00eb_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(D|(~A&((B|C)&(~B|~C))));
endmodule
module dd2_g5__f009f_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(D|(C&((A|B)&(~A|~B))));
endmodule
module dd2_g5__feee8_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(~((A&B)|((A|B)&(C|D))));
endmodule
module dd2_g5__f008e_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(D|((~A|~B)&(C|(~A&~B))));
endmodule
module dd2_g5__f00be_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(D|(~A&((B&C)|(~B&~C))));
endmodule
module dd2_g5__fa888_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(~(A&(B|(C&D))));
endmodule
module dd2_g5__f006f_1 (A, B, C, D, Y);
  input A, B, C, D;
  output Y;
  assign Y = ~(D|(C&((A&B)|(~A&~B))));
endmodule
