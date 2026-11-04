/* Host test for the playlist catalog's Back navigation (y2dj-playlists-aiff.patch).
 *
 * test_catalog_paths.py pulls two pieces of new code out of the patch:
 *   reopen.inc  catalog_reopen_path() from apps/playlist_catalog.c
 *   browse.inc  the "open at selected" block from rockbox_browse() in apps/tree.c
 * and builds this file with them, against a mock Playlists folder.
 *
 * usage: catalog_paths_test <dir containing Playlists/>
 */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>

#define MAX_PATH 260
#define PATH_SEPCH '/'

/* --- the Rockbox pieces the patched code uses ------------------------------ */

static char most_recent_playlist[MAX_PATH];

/* Rockbox's strmemccpy: copy at most n - 1 chars, always terminate. */
static char *strmemccpy(char *dst, const char *src, size_t n)
{
    size_t i = 0;
    for (; i + 1 < n && src[i]; i++)
        dst[i] = src[i];
    dst[i] = '\0';
    return dst + i + 1;
}

/* Rockbox's strlcat (BSD semantics). glibc may not declare one under -std=c99,
 * so use our own everywhere. */
static size_t test_strlcat(char *dst, const char *src, size_t size)
{
    size_t d = strlen(dst), s = strlen(src);
    if (d + 1 < size)
    {
        size_t n = (s < size - d - 1) ? s : size - d - 1;
        memcpy(dst + d, src, n);
        dst[d + n] = '\0';
    }
    return d + s;
}
#undef strlcat /* macOS defines it as a macro */
#define strlcat test_strlcat

static bool dir_exists(const char *path)
{
    struct stat st;
    return stat(path, &st) == 0 && S_ISDIR(st.st_mode);
}

static struct { char currdir[MAX_PATH]; char lastfile[MAX_PATH]; int dirlevel; } tc;

/* The parts of tree.c's set_current_file_ex the browser outcome depends on:
 * which folder opens and which file is looked for in it. */
static void set_current_file_ex(const char *path, const char *filename)
{
    if (!filename)
    {
        const char *f = strrchr(path + 1, '/');
        size_t endpos = f - path;
        memcpy(tc.currdir, path, endpos);
        tc.currdir[endpos] = '\0';
        filename = f + 1;
    }
    else
        snprintf(tc.currdir, sizeof(tc.currdir), "%s", path);
    snprintf(tc.lastfile, sizeof(tc.lastfile), "%s", filename);
    tc.dirlevel = 99; /* the real one counts from /; the patch must reset it */
}

/* --- the patched code ------------------------------------------------------ */

#include "reopen.inc"

static void browse_open(const char *root, const char *selected)
{
    struct { const char *root, *selected; } ctx = { root, selected }, *browse = &ctx;
#include "browse.inc"
}

/* --- cases ----------------------------------------------------------------- */

static int failures;

static void check(const char *name, const char *root, const char *recent, bool top_only,
                  const char *want_dir, const char *want_file, int want_level)
{
    char rel[MAX_PATH];
    snprintf(most_recent_playlist, sizeof(most_recent_playlist), "%s", recent);
    catalog_reopen_path(rel, sizeof(rel), root, top_only);
    browse_open(root, rel);
    bool ok = !strcmp(tc.currdir, want_dir) && !strcmp(tc.lastfile, want_file)
              && tc.dirlevel == want_level;
    if (!ok)
    {
        failures++;
        printf("FAIL %s\n  got  dir=%s file=%s level=%d\n  want dir=%s file=%s level=%d\n",
               name, tc.currdir, tc.lastfile, tc.dirlevel, want_dir, want_file, want_level);
    }
    else
        printf("ok   %s\n", name);
}

int main(int argc, char **argv)
{
    if (argc != 2)
        return 2;
    char root[MAX_PATH], root_slash[MAX_PATH], emotion[MAX_PATH], system[MAX_PATH];
    char happy[MAX_PATH], p[MAX_PATH];
    snprintf(root, sizeof(root), "%s/Playlists", argv[1]);
    snprintf(root_slash, sizeof(root_slash), "%s/", root);
    snprintf(system, sizeof(system), "%s/System 2023", root);
    snprintf(emotion, sizeof(emotion), "%s/System 2023/Emotion", root);
    snprintf(happy, sizeof(happy), "%s/HAPPY.m3u8", emotion);

    /* Ben's report: Playlists > System 2023 > Emotion > HAPPY, then Back. */
    check("back from a nested playlist opens its folder", root, happy, false,
          emotion, "HAPPY.m3u8", 2);
    check("catalog dir set with a trailing slash", root_slash, happy, false,
          emotion, "HAPPY.m3u8", 2);
    snprintf(p, sizeof(p), "%s//System 2023/Emotion/HAPPY.m3u8", root);
    check("doubled slash in the saved path", root, p, false, emotion, "HAPPY.m3u8", 2);
    snprintf(p, sizeof(p), "%s/System 2023/Mix.m3u8", root);
    check("back from one level down", root, p, false, system, "Mix.m3u8", 1);
    snprintf(p, sizeof(p), "%s/Top.m3u8", root);
    check("back from a top-level playlist", root, p, false, root, "Top.m3u8", 0);

    /* Opening the catalog from the main menu starts at the top level. */
    check("main menu opens the top level at the last folder", root, happy, true,
          root, "System 2023", 0);
    check("main menu with a top-level last playlist", root, p, true, root, "Top.m3u8", 0);

    /* Nothing may strand the browser in a folder that isn't there. */
    check("no recent playlist", root, "", false, root, "", 0);
    snprintf(p, sizeof(p), "%s/Gone/List.m3u8", root);
    check("folder deleted since", root, p, false, root, "Gone/List.m3u8", 0);
    check("recent playlist outside the catalog", root, "/elsewhere/A/B.m3u8", false,
          root, "", 0);
    snprintf(p, sizeof(p), "%sOld/A/B.m3u8", root);
    check("sibling folder with a similar name", root, p, false, root, "", 0);
    snprintf(p, sizeof(p), "%s/System 2023/", root);
    check("path ending in a slash", root, p, false, root, "System 2023/", 0);

    printf("%d failure(s)\n", failures);
    return failures != 0;
}
