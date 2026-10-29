/* Private C-locale data and native NeXT time structure bridge.
   SPDX-License-Identifier: 0BSD */
#include <time.h>
typedef int nl_item;
enum {
  ABDAY_1 = 0, DAY_1 = 7, ABMON_1 = 14, MON_1 = 26,
  AM_STR = 38, PM_STR, D_T_FMT, D_FMT, T_FMT, T_FMT_AMPM
};
static const char *ns33_time_info(nl_item item)
{
  static const char *const values[] = {
    "Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat",
    "Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday",
    "Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec",
    "January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December",
    "AM", "PM", "%a %b %e %T %Y", "%m/%d/%y", "%H:%M:%S", "%I:%M:%S %p"
  };
  return values[item];
}
long long ns33_year_to_secs(long long, int *);
int ns33_month_to_secs(int, int);
long long ns33_tm_to_secs(const struct tm *);
size_t ns33_strftime_core(char *, size_t, const char *, const struct tm *, int);
extern size_t ns33_native_strftime(char *, size_t, const char *, const struct tm *) __asm__("_strftime");
