#import <appkit/Application.h>
#import <appkit/Window.h>
#import <appkit/Button.h>
#import <dpsclient/dpsNeXT.h>
#include <stdio.h>

static void complete(DPSTimedEntry entry, double now, void *context)
{
  (void)now;
  (void)context;
  DPSRemoveTimedEntry(entry);
  puts("appkit probe: passed");
  fflush(stdout);
  [NXApp terminate:nil];
}

@interface CompilerProbe : Object
- appDidInit:sender;
@end
@implementation CompilerProbe
- appDidInit:sender
{
  NXRect frame = {{100, 100}, {300, 120}};
  NXRect buttonFrame = {{30, 35}, {240, 35}};
  id window = [[Window alloc] initContent:&frame style:NX_TITLEDSTYLE
                   backing:NX_BUFFERED buttonMask:NX_CLOSEBUTTONMASK defer:NO];
  id button = [[Button alloc] initFrame:&buttonFrame];
  [window setTitle:"Modern GCC AppKit probe"];
  [button setTitle:"Native NeXT controls"];
  [[window contentView] addSubview:button];
  [window display];
  [window orderFront:nil];
  DPSAddTimedEntry(2.0, complete, 0, NX_BASETHRESHOLD);
  return self;
}
@end

int main(void)
{
  id delegate = [CompilerProbe new];
  [Application new];
  [NXApp setDelegate:delegate];
  [NXApp run];
  return 1;
}
