/* Numeric HI/LO boundaries must not use NeXT's 8 KiB symbol rounding.
   SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#define FN(n,v) __attribute__((noinline)) unsigned n(void){return v;}
FN(a,18432U) FN(b,2048U) FN(c,4096U) FN(d,6144U)
FN(e,0x12345800U) FN(f,0xffffe800U) FN(g,0x12345678U)
int main(void){unsigned x[]={a(),b(),c(),d(),e(),f(),g()};const char *text[]={"4800","800","1000","1800","12345800","ffffe800","12345678"};unsigned want;int i,bad=0;for(i=0;i<7;i++){if(sscanf(text[i],"%x",&want)!=1)return 2;printf("%d:%08x expected:%08x\n",i,x[i],want);if(x[i]!=want)bad++;}printf("CONSTANT_FAILURES:%d\n",bad);return bad!=0;}
