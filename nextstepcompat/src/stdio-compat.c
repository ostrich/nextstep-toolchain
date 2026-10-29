/* Supply pushback space at the beginning of a native NeXT input buffer.
   Native fclose/fseek/getc keep owning all stream state. SPDX-License-Identifier: 0BSD */
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <limits.h>
#include <errno.h>
#include <unistd.h>
extern int native_ungetc(int, FILE *) __asm__("_ungetc");
extern size_t native_fwrite(const void *, size_t, size_t, FILE *) __asm__("_fwrite");

int ns33_ungetc(int c, FILE *file)
{
  int result;
  if (c == EOF) return EOF;
  c = (unsigned char)c;
  /* Repeated native getc at EOF can leave a negative count. It describes no
     unread data, but native ungetc rejects it at the buffer's beginning. */
  if ((file->_flag & _IOEOF) && file->_cnt < 0) file->_cnt = 0;
  if ((file->_flag & _IORW) && (file->_flag & _IOWRT)) {
    if (fflush(file)) return EOF;
    file->_flag &= ~_IOWRT;
    file->_cnt = 0;
    file->_ptr = file->_base;
  }
  if (file->_flag & _IORW) file->_flag |= _IOREAD;
  if ((file->_flag & (_IOREAD | _IORW)) && file->_base &&
      file->_ptr == file->_base && file->_cnt > 0) {
    /* The old implementation rejects this case even for a single pushback.
       Reserve space without discarding the unread data or freeing a caller's
       setvbuf array. Native fclose frees only buffers marked _IOMYBUF. */
    if (file->_cnt >= file->_bufsiz) {
      char *buffer;
      if (file->_cnt == INT_MAX) { errno = EOVERFLOW; return EOF; }
      buffer = malloc((size_t)file->_cnt + 1);
      if (!buffer) { errno = ENOMEM; return EOF; }
      memcpy(buffer + 1, file->_base, (size_t)file->_cnt);
      if (file->_flag & _IOMYBUF) free(file->_base);
      file->_base = buffer;
      file->_bufsiz = file->_cnt + 1;
      file->_flag |= _IOMYBUF;
    } else {
      memmove(file->_base + 1, file->_base, (size_t)file->_cnt);
    }
    file->_ptr = file->_base + 1;
  }
  result = native_ungetc(c, file);
  if (result != EOF) {
    file->_flag &= ~_IOEOF;
    file->_flag |= _IOREAD;
  }
  return result;
}

/* The native fwrite can reject a read-only stream without setting _IOERR. */
size_t ns33_fwrite(const void *text, size_t size, size_t count, FILE *file)
{
  size_t result;
  if (!size || !count) return 0;
  if (!(file->_flag & (_IOWRT | _IORW))) {
    file->_flag |= _IOERR;
    errno = EBADF;
    return 0;
  }
  if ((file->_flag & _IORW) && !(file->_flag & _IOWRT)) {
    /* Native fseek clears the direction flags. Native line-buffered fwrite
       then reports success without setting _IOWRT, so fflush drops the write.
       Establish output mode. Reconcile any retained read buffer first. */
    if ((file->_flag & _IOREAD) && file->_cnt > 0 &&
        lseek(file->_file, -(off_t)file->_cnt, SEEK_CUR) == (off_t)-1) {
      file->_flag |= _IOERR;
      return 0;
    }
    file->_cnt = 0;
    file->_ptr = file->_base;
    file->_flag &= ~_IOREAD;
    file->_flag |= _IOWRT;
  }
  result = native_fwrite(text, size, count, file);
  if (result != count) file->_flag |= _IOERR;
  return result;
}

size_t ns33_stream_write(FILE *file, const char *text, size_t length)
{
  return ns33_fwrite(text, 1, length, file);
}
