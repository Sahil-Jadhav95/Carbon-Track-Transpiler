const width = 2 * 3;
const height = 10 + 5;
const secondsInDay = 60 * 60 * 24;

function computeSquare(x) {
  return x ** 2;
}

function computeCube(x) {
  return x ** 3;
}

let result = 0;
result = 42;

const a = result * 1;
const b = result + 0;
const c = result - 0;
const d = result ** 1;
const e = result / 1;

const flag = true;
if (flag === true) {
  console.log("Flag is on");
}
if (flag === false) {
  console.log("Flag is off");
}
if (flag !== true) {
  console.log("Flag is not on");
}

function greet(name) {
  return `Hello, ${name}`;
  console.log("This will never run");
}

const color = "red";
if (["red", "green", "blue"].includes(color)) {
  console.log("Primary color");
}
if (![1, 2, 3, 4].includes(5)) {
  console.log("Not found");
}

const squares = [];
for (let i = 0; i < 10; i++) {
  squares.push(i ** 2);
}

const doubled = [];
for (let x = 0; x < 5; x++) {
  doubled.push(x * 2);
}

function energyFormula(mass) {
  const c = 3 * 100000000;
  return mass * c ** 2;
}

console.log("Width:", width);
console.log("Height:", height);
console.log("Seconds in a day:", secondsInDay);
console.log("Square of 5:", computeSquare(5));
console.log("Cube of 3:", computeCube(3));
console.log("Result:", result);
console.log("a:", a, "b:", b, "c:", c, "d:", d, "e:", e);
console.log("Greet:", greet("World"));
console.log("Squares:", squares);
console.log("Doubled:", doubled);
console.log("Energy:", energyFormula(1));
