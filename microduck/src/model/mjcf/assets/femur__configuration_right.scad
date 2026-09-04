% scale(1000) import("femur__configuration_right.stl");

// Append pure shapes (cube, cylinder and sphere), e.g:
// cube([10, 10, 10], center=true);
// cylinder(r=10, h=10, center=true);
// sphere(10);

translate([-17.25, 18, 99.213])
cube([2.5, 18, 44.456], center=true);

translate([-17.25, 11.818, 123.895])
rotate([45, 0, 0])
cube([2.5, 18, 24.941], center=true);

translate([-17.25, 14.318, 77.031])
rotate([-45, 0, 0])
cube([2.5, 18, 17.87], center=true);
