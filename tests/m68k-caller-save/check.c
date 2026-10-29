/* SPDX-License-Identifier: MIT */
/* Separate translation unit: calls must remain opaque to the optimizer. */
#include <stdarg.h>
#include <stdio.h>
#include <string.h>
struct rect {
    float x, y, w, h;
};
struct state {
    void *window, *toolbar, *scroll, *url, *buttons[3];
};
extern void layout(struct state *);
static int failures, checks, object;
void *message(void *receiver, const char *operation, ...) {
    va_list args;
    struct rect *r;
    float *size;
    float width = 0, height = 0;
    int check = 0, ok;
    (void)receiver;
    va_start(args, operation);
    if (strcmp(operation, "screen") == 0) {
        size = va_arg(args, float *);
        size[0] = 1120;
        size[1] = 832;
    } else {
        if (strcmp(operation, "init") == 0) {
            width = 720;
            height = 480;
            check = 1;
        }
        if (strcmp(operation, "toolbar") == 0) {
            width = 720;
            height = 40;
            check = 1;
        }
        if (strcmp(operation, "url") == 0) {
            width = 516;
            height = 22;
            check = 1;
        }
        if (strcmp(operation, "scroll") == 0) {
            width = 720;
            height = 440;
            check = 1;
        }
        if (check) {
            r = va_arg(args, struct rect *);
            ok = r->w == width && r->h == height;
            printf("FLOAT-FRAME %s %s %g %g\n", ok ? "PASS" : "FAIL", operation,
                   (double)r->w, (double)r->h);
            checks++;
            if (!ok)
                failures++;
        }
    }
    va_end(args);
    return &object;
}
int main(void) {
    struct state state;
    memset(&state, 0, sizeof(state));
    layout(&state);
    printf("FLOAT-FRAME-SUITE failures=%d checks=%d\n", failures, checks);
    return failures || checks != 4;
}
