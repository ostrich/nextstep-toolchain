/* SPDX-License-Identifier: MIT */
/* Reduced from native browser layout. Keep calls in a separate object. */
struct rect {
    float x, y, w, h;
};
struct state {
    void *window, *toolbar, *scroll, *url, *buttons[3];
};
extern void *message(void *, const char *, ...);
static struct rect make(float x, float y, float w, float h) {
    struct rect r = {x, y, w, h};
    return r;
}
void layout(struct state *self) {
    float screen[2], width = 720, height = 480;
    struct rect r;
    void *content;
    message(0, "screen", screen);
    if (screen[0] > 0 && screen[0] < 844)
        width = screen[0] - 124;
    if (screen[1] > 0 && screen[1] < 560)
        height = screen[1] - 80;
    if (width < 320)
        width = 320;
    if (height < 240)
        height = 240;
    r = make(60, 40, width, height);
    if (self->window)
        return;
    self->window = message(message(0, "alloc"), "init", &r, 6, 2, 5, 0);
    message(self->window, "title", "test");
    message(self->window, "free", 0);
    message(self->window, "delegate", self);
    message(self->window, "event", 32);
    content = message(self->window, "content");
    r = make(0, height - 40, width, 40);
    self->toolbar = message(message(0, "alloc"), "toolbar", &r);
    message(self->toolbar, "auto", 1);
    message(self->toolbar, "sizing", 10);
    message(content, "add", self->toolbar);
    self->buttons[0] = message(self->toolbar, "button", 6, 50);
    self->buttons[1] = message(self->toolbar, "button", 60, 66);
    self->buttons[2] = message(self->toolbar, "button", 130, 62);
    r = make(198, 9, width - 204, 22);
    self->url = message(message(0, "alloc"), "url", &r);
    message(self->url, "bezel", 1);
    message(self->url, "edit", 1);
    message(self->url, "select", 1);
    message(self->url, "target", self);
    message(self->url, "action", 0);
    message(self->url, "size", 2);
    message(self->toolbar, "add", self->url);
    r = make(0, 0, width, height - 40);
    self->scroll = message(message(0, "alloc"), "scroll", &r);
}
