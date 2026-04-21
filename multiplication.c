/ * Author: Eugénie
 * Date  : April 2026
 *
 * Task tau_1: computes the product of two large randomly-generated
 * numbers using a naive O(n^2) big-integer multiplication algorithm.
 *
 * The purpose of this program is NOT to perform an efficient
 * multiplication (Karatsuba or FFT-based methods would be much faster),
 * but to provide a CPU-bound, deterministic-in-structure workload whose
 * worst-case execution time (WCET) can be measured empirically and used
 * as C_1 in the scheduling analysis done by scheduler.py.
 *
 * Compile: gcc -O0 -o multiplication.exe multiplication.c
 * Run:     ./multiplication.exe
 *
 * On stdout, the program prints exactly one floating-point value:
 * the elapsed execution time of bigmul() in microseconds.
 * measurement.py captures this value over many runs to build WCET stats.
 *
 * Important: the -O0 flag is mandatory. With -O2/-O3 the compiler can
 * detect that the result C is never used, or partially unroll/vectorize
 * the loops, which would drastically change (or even eliminate) the
 * measured workload. -O0 keeps the algorithm faithful to its source.
 */

 

#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <time.h>

#ifdef _WIN32
#include <windows.h>
#endif

#define NUM_DIGITS 1000  /* number of digits per operand */

/* Naive big-integer multiplication using digit arrays (base 10).
 * A has na digits, B has nb digits, result C has na+nb digits.
 * Digits stored least-significant first. */
static void bigmul(const int *A, int na, const int *B, int nb, int *C) {
    int nc = na + nb;
    memset(C, 0, nc * sizeof(int));
    for (int i = 0; i < na; i++) {
        int carry = 0;
        for (int j = 0; j < nb; j++) {
            int tmp = C[i + j] + A[i] * B[j] + carry;
            C[i + j] = tmp % 10;
            carry = tmp / 10;
        }
        C[i + nb] += carry;
    }
}

static double get_time_us(void) {
#ifdef _WIN32
    LARGE_INTEGER freq, cnt;
    QueryPerformanceFrequency(&freq);
    QueryPerformanceCounter(&cnt);
    return (double)cnt.QuadPart / (double)freq.QuadPart * 1e6;
#else
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec * 1e6 + ts.tv_nsec / 1e3;
#endif
}

int main(void) {
    int *A = malloc(NUM_DIGITS * sizeof(int));
    int *B = malloc(NUM_DIGITS * sizeof(int));
    int *C = malloc(2 * NUM_DIGITS * sizeof(int));

    srand((unsigned)time(NULL));
    for (int i = 0; i < NUM_DIGITS; i++) {
        A[i] = rand() % 10;
        B[i] = rand() % 10;
    }

    double start = get_time_us();
    bigmul(A, NUM_DIGITS, B, NUM_DIGITS, C);
    double end = get_time_us();

    printf("%.2f\n", end - start);

    free(A);
    free(B);
    free(C);
    return 0;
}
