const width = 2 + 3;
const height = 10 * 1;
let result = 0;
result = 42;

function square(x) {
  return x * x;
  console.log("unreachable");
}

function cube(x) {
  return x ** 3;
}

const a = 5 + 5;
const b = 5 + 5;

if (true === true) {
  console.log("always runs");
}

let items = ["a", "b", "c"];
let output = "";
for (const ch of items) {
  output += ch;
}

for (let i = 0; i < items.length; i++) {
  console.log(items[i]);
}
for (let i = 0; i < items.length; i++) {
  console.log(items[i] + "!");
}

const temp = width + 0;
console.log(square(5));
console.log(cube(2));
console.log(output);
