// Test: is the constructor of a global object compiled by clang (AIX target)
// run, depending on how it is linked on IBM i (gcc driver, ld -bcdtors)?
#include <stdio.h>
struct A {
  int v;
  A() : v(42) { puts("constructeur global execute"); }
};
A a;
int main() {
  printf("a.v = %d\n", a.v);
  return 0;
}
