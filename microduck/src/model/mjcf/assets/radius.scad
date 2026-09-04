% scale(1000) import("radius.stl");

// Append pure shapes (cube, cylinder and sphere), e.g:
// cube([10, 10, 10], center=true);
// cylinder(r=10, h=10, center=true);
// sphere(10);

translate([-33.7, 0, -27])
rotate([0, 90, 0])
cylinder(r=9, h=33.5, center=true);

translate([-33.7, 0, -27-67.014])
rotate([0, 90, 0])
cylinder(r=5.25, h=16, center=true);