#import <foundation/NSString.h>
#include <stdio.h>
#include <string.h>

/* NXConstantString is the classic NXString object, including on 4.2.  Its
   API differs from the NSConstantString used by the later Foundation.  */
@interface NXConstantString (ClassicStringProbe)
- (unsigned int)cStringLength;
- getCString:(char *)buffer;
@end

int main(void)
{
  NXConstantString *first = @"classic string";
  NXConstantString *second = @"another constant";
  char buffer[40];
  [first getCString:buffer];
  if (strcmp(buffer, "classic string")) return 1;
  [second getCString:buffer];
  if (strcmp(buffer, "another constant")) return 2;
  if ([first cStringLength] != 14 || [second cStringLength] != 16) return 3;
  printf("objc constants: passed\n");
  return 0;
}
