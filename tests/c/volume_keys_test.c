/* Host test for y2dj-volume-keys.patch: the Y2 volume keys reach Rockbox as
 * queued press/release events, like the D-pad, so quick taps aren't lost.
 *
 * test_volume_keys.py pulls the new block out of the patch (volume.inc) and
 * builds it into a stand-in for buttonHandler, with the queue mocked.
 */
#include <stdbool.h>
#include <stdio.h>

#define KEYCODE_VOLUME_UP   24
#define KEYCODE_VOLUME_DOWN 25
#define KEYCODE_DPAD_UP     19
#define BUTTON_VOL_UP       0x00000080
#define BUTTON_VOL_DOWN     0x00000100
#define BUTTON_REL          0x02000000

static unsigned posted[16];
static int nposted, ready_waits, poweroff_resets;

static void button_queue_post(long id, long data) { (void)data; posted[nposted++] = (unsigned)id; }
static void wait_rockbox_ready(void) { ready_waits++; }
static void reset_poweroff_timer(void) { poweroff_resets++; }

/* What buttonHandler does after the long-press block passes a key through. */
static bool handler(int keycode, bool state)
{
#include "volume.inc"
    return false; /* fell through to the rest of buttonHandler */
}

static int failures;
#define CHECK(cond, what) do { if (cond) printf("ok   %s\n", what); \
    else { failures++; printf("FAIL %s\n", what); } } while (0)

int main(void)
{
    nposted = 0;
    CHECK(handler(KEYCODE_VOLUME_UP, true), "volume up press is consumed");
    CHECK(handler(KEYCODE_VOLUME_UP, false), "volume up release is consumed");
    CHECK(nposted == 2 && posted[0] == BUTTON_VOL_UP
          && posted[1] == (BUTTON_VOL_UP | BUTTON_REL),
          "volume up posts a press then a release");

    nposted = 0;
    handler(KEYCODE_VOLUME_DOWN, true);
    handler(KEYCODE_VOLUME_DOWN, false);
    CHECK(nposted == 2 && posted[0] == BUTTON_VOL_DOWN
          && posted[1] == (BUTTON_VOL_DOWN | BUTTON_REL),
          "volume down posts a press then a release");

    /* A tap whose down and up arrive back to back still makes one step. */
    nposted = 0;
    handler(KEYCODE_VOLUME_UP, true);
    handler(KEYCODE_VOLUME_UP, false);
    handler(KEYCODE_VOLUME_UP, true);
    handler(KEYCODE_VOLUME_UP, false);
    int presses = 0;
    for (int i = 0; i < nposted; i++)
        presses += posted[i] == BUTTON_VOL_UP;
    CHECK(presses == 2, "two quick taps make two presses");

    CHECK(ready_waits == poweroff_resets && ready_waits == 8,
          "every event waits for Rockbox and resets the idle timer");

    nposted = 0;
    CHECK(!handler(KEYCODE_DPAD_UP, true) && nposted == 0,
          "other keys are left to the rest of buttonHandler");

    printf("%d failure(s)\n", failures);
    return failures != 0;
}
