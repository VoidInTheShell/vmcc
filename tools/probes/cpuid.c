// SPDX-License-Identifier: GPL-2.0-or-later
#define _GNU_SOURCE
#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <unistd.h>
#include <sched.h>
#include <time.h>
#include <cpuid.h>
#include <x86intrin.h>
static uint64_t ns(void){struct timespec t;clock_gettime(CLOCK_MONOTONIC_RAW,&t);return (uint64_t)t.tv_sec*1000000000+t.tv_nsec;}
static int cmp(const void *a,const void *b){uint64_t x=*(uint64_t*)a,y=*(uint64_t*)b;return (x>y)-(x<y);}
int main(void){
 unsigned a,b,c,d,junk;cpu_set_t s;
 for(int cpu=0;cpu<24;cpu++){
  CPU_ZERO(&s);CPU_SET(cpu,&s);if(sched_setaffinity(0,sizeof(s),&s))return 2;
  __cpuid_count(1,0,a,b,c,d);printf("CPU %d signature=%08x apic=%u hypervisor=%u",cpu,a,b>>24,(c>>31)&1);
  __cpuid_count(0x1a,0,a,b,c,d);printf(" core_type=%02x",a>>24);
  __cpuid_count(0xb,0,a,b,c,d);printf(" smt_shift=%u smt_count=%u",a,b);
  __cpuid_count(0xb,1,a,b,c,d);printf(" pkg_threads=%u",b);
  __cpuid_count(7,0,a,b,c,d);printf(" hybrid=%u\n",(d>>15)&1);
  for(int sub=0;sub<4;sub++){
   __cpuid_count(4,sub,a,b,c,d);
   uint64_t size=((b&4095)+1ULL)*(((b>>12)&1023)+1ULL)*((b>>22)+1ULL)*(c+1ULL);
   printf(" cache%u level=%u type=%u bytes=%llu sharing_ids=%u\n",sub,(a>>5)&7,a&31,(unsigned long long)size,((a>>14)&4095)+1);
  }
  uint64_t times[1000];int backwards=0;
  for(int k=0;k<1000;k++){_mm_lfence();uint64_t st=__rdtsc();__cpuid_count(0,0,a,b,c,d);uint64_t en=__rdtscp(&junk);_mm_lfence();times[k]=en-st;if(en<st)backwards++;}
  qsort(times,1000,sizeof(uint64_t),cmp);
  uint64_t n0=ns(),t0=__rdtsc();struct timespec req={0,20000000};nanosleep(&req,0);uint64_t t1=__rdtsc(),n1=ns();
  printf(" timing cpuid_cycles_p50=%llu p99=%llu backwards=%d tsc_mhz=%.3f\n",(unsigned long long)times[500],(unsigned long long)times[990],backwards,(double)(t1-t0)*1000/(n1-n0));
 }
 return 0;
}
