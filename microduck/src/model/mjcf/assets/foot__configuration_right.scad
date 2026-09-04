% scale(1000) import("foot.stl");

// Append pure shapes (cube, cylinder and sphere), e.g:
// cube([10, 10, 10], center=true);
// cylinder(r=10, h=10, center=true);
// sphere(10);

translate([0, 3.5, -12.25])
cube([45, 80, 2.5], center=true);

translate([0, 3.5, -12.25])
cube([35, 90, 2.5], center=true);

translate([17.5, -36.5, -12.25])
rotate([0, 0, 45])
cube([sqrt(50), sqrt(50), 2.5], center=true);

translate([-17.5, -36.5, -12.25])
rotate([0, 0, 45])
cube([sqrt(50), sqrt(50), 2.5], center=true);

translate([17.5, 43.5, -12.25])
rotate([0, 0, 45])
cube([sqrt(50), sqrt(50), 2.5], center=true);

translate([-17.5, 43.5, -12.25])
rotate([0, 0, 45])
cube([sqrt(50), sqrt(50), 2.5], center=true);
