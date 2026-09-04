% scale(1000) import("pelvis__configuration_right.stl");

// Append pure shapes (cube, cylinder and sphere), e.g:
// cube([10, 10, 10], center=true);
// cylinder(r=10, h=10, center=true);
// sphere(10);

translate([36, 5.75, 102.15])
cube([108, 16, 107.5], center=true);

translate([36, 5.75, 102.15+4])
cube([58, 66, 85.5], center=true);