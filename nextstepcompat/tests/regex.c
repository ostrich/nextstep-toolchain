/* POSIX regex behavior, captures and single-byte offsets. SPDX-License-Identifier: 0BSD */
#include <regex.h>
#include <stdio.h>
#include <string.h>
#include <stdlib.h>

static unsigned checks, failures;
static void check(int ok,const char *name)
{
    ++checks;
    if(!ok){++failures;printf("FAIL %s\n",name);}
}
struct sample {
    const char *pattern,*text;
    int compile_flags,execute_flags,result;
    int start,end;
};
static const struct sample samples[]={
    {"abc","xxabczz",REG_EXTENDED,0,0,2,5},
    {"abc","ab",REG_EXTENDED,0,REG_NOMATCH,0,0},
    {"","abc",REG_EXTENDED,0,0,0,0},
    {"a|ab","zabx",REG_EXTENDED,0,0,1,3},
    {"ab*","abbb",REG_EXTENDED,0,0,0,4},
    {"ab+","abbb",REG_EXTENDED,0,0,0,4},
    {"ab?","a",REG_EXTENDED,0,0,0,1},
    {"[a-z]{2,4}","123abcde",REG_EXTENDED,0,0,3,7},
    {"[[:digit:]]+","x123z",REG_EXTENDED,0,0,1,4},
    {"[[:alpha:]_]+","123_aBc",REG_EXTENDED,0,0,3,7},
    {"[^a]+","aXYZaa",REG_EXTENDED,0,0,1,4},
    {"^[[:space:]]+$"," \t",REG_EXTENDED,0,0,0,2},
    {"abc","aBc",REG_EXTENDED|REG_ICASE,0,0,0,3},
    {"^abc$","abc",REG_EXTENDED,REG_NOTBOL,REG_NOMATCH,0,0},
    {"^abc$","abc",REG_EXTENDED,REG_NOTEOL,REG_NOMATCH,0,0},
    {"^abc$","x\nabc\ny",REG_EXTENDED|REG_NEWLINE,0,0,2,5},
    {"a.b","a\nb",REG_EXTENDED,0,0,0,3},
    {"a.b","a\nb",REG_EXTENDED|REG_NEWLINE,0,REG_NOMATCH,0,0},
    {"[^a]+","\nb",REG_EXTENDED|REG_NEWLINE,0,0,1,2},
    {"a\\{2,3\\}","aaa",0,0,0,0,3},
    {"\\(ab\\)\\1","xababz",0,0,0,1,5},
    {"^a$","a",0,0,0,0,1},
    {"\\+","+",REG_EXTENDED,0,0,0,1},
    {"\\.","a.b",REG_EXTENDED,0,0,1,2},
    {"[]a]", "]",REG_EXTENDED,0,0,0,1},
    {"\377+","x\377\377z",REG_EXTENDED,0,0,1,3},
    {"[^x]+","x\200\377",REG_EXTENDED,0,0,1,3},
    {"[[.d.]]..","dog",REG_EXTENDED,0,0,0,3},
    {"[[=d=]]..","dog",REG_EXTENDED,0,0,0,3},
    {"[[=d=]]..","Dog",REG_EXTENDED,0,REG_NOMATCH,0,0},
    {"[[=d=]]..","Dog",REG_EXTENDED|REG_ICASE,0,0,0,3},
    {"[[.a.]-[.c.]]+","zabcx",REG_EXTENDED,0,0,1,4},
    {"[a-[.c.]]+","zabcx",REG_EXTENDED,0,0,1,4},
    {"[[.a.]-c]+","zabcx",REG_EXTENDED,0,0,1,4},
    {"[[.].]]", "]",REG_EXTENDED,0,0,0,1},
    {"[[.-.]]", "-",REG_EXTENDED,0,0,0,1},
    {"[[.^.]]", "^",REG_EXTENDED,0,0,0,1},
    {"[[.\377.]]+","x\377\377z",REG_EXTENDED,0,0,1,3},
    {"[^[.d.]]","x",REG_EXTENDED,0,0,0,1},
    {"[^d]","d",REG_EXTENDED,0,REG_NOMATCH,0,0},
    {"[^[.d.]]","d",REG_EXTENDED,0,REG_NOMATCH,0,0}
};
static void captures(void)
{
    regex_t r;regmatch_t m[5];int status;
    status=regcomp(&r,"(a)?(b*)",REG_EXTENDED);check(status==0,"capture compile");
    if(status)return;
    check(r.re_nsub==2,"capture count");
    memset(m,0,sizeof(m));status=regexec(&r,"bbb",5,m,0);
    check(status==0,"capture execute");
    check(m[0].rm_so==0&&m[0].rm_eo==3,"whole match");
    check(m[1].rm_so==-1&&m[1].rm_eo==-1,"absent group");
    check(m[2].rm_so==0&&m[2].rm_eo==3,"present group");
    check(m[3].rm_so==-1&&m[3].rm_eo==-1&&m[4].rm_so==-1&&m[4].rm_eo==-1,"unused slots");
    check(regexec(&r,"bbb",0,NULL,0)==0,"no match vector");regfree(&r);
    status=regcomp(&r,"(ab)+",REG_EXTENDED|REG_NOSUB);check(status==0,"nosub compile");
    if(!status){check(regexec(&r,"abab",0,NULL,0)==0,"nosub execute");regfree(&r);}
}
static void errors(void)
{
    static const struct {const char *pattern;int error;} bad[]={
        {"[abc",REG_EBRACK},{"(",REG_EPAREN},{"a{3,2}",REG_BADBR},
        {"[z-a]",REG_ERANGE},{"[[:unknown:]]",REG_ECTYPE},{"\\",REG_EESCAPE},
        {"[[.ab.]]",REG_ECOLLATE},{"[[=ab=]]",REG_ECOLLATE},
        {"[[..]]",REG_ECOLLATE},{"[[==]]",REG_ECOLLATE},
        {"[[.a.]",REG_EBRACK},{"[[=a=]-c]",REG_ERANGE},
        {"[a-[=c=]]",REG_ERANGE},{"[[.z.]-[.a.]]",REG_ERANGE}
    };
    unsigned i;regex_t r;char message[128],small[3];size_t need;
    for(i=0;i<sizeof(bad)/sizeof(bad[0]);i++){
        int e=regcomp(&r,bad[i].pattern,REG_EXTENDED);
        check(e==bad[i].error,bad[i].pattern);
        if(e==0){regfree(&r);continue;}
        need=regerror(e,&r,NULL,0);check(need>1,"error size");
        check(regerror(e,&r,message,sizeof(message))==need,"error size stable");
        check(strlen(message)+1==need,"error terminator");
        memset(small,'x',sizeof(small));
        check(regerror(e,&r,small,sizeof(small))==need&&small[2]==0,"error truncation");
    }
}
int main(void)
{
    unsigned i;regex_t r;regmatch_t m[1];int status;
    for(i=0;i<sizeof(samples)/sizeof(samples[0]);i++){
        const struct sample *s=&samples[i];
        status=regcomp(&r,s->pattern,s->compile_flags);
        check(status==0,s->pattern);if(status)continue;
        status=regexec(&r,s->text,1,m,s->execute_flags);check(status==s->result,s->pattern);
        if(!status)check(m[0].rm_so==s->start&&m[0].rm_eo==s->end,"sample offsets");
        regfree(&r);
    }
    captures();errors();
    for(i=0;i<200;i++){
        status=regcomp(&r,"^([[:alnum:]_]+)(-[0-9]{1,3})?$",REG_EXTENDED);
        check(status==0,"repeat compile");if(status)break;
        check(regexec(&r,"hello-42",1,m,0)==0&&m[0].rm_so==0&&m[0].rm_eo==8,"repeat match");regfree(&r);
    }
    printf("REGEX: %u checks, %u failures\n",checks,failures);return failures!=0;
}
