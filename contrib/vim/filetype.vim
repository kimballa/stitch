" Put this file in your ~/.vim directory to autodetect "targets" files as
" Stitch targets files for syntax highlighting purposes.
"
" If you've already got a filetype.vim in there, add the au! line to the 
" existing filetypedetect augroup block.

if exists("did_load_filetypes")
  finish
endif
augroup filetypedetect
  au! BufRead,BufNewFile targets setfiletype stitch
augroup END

