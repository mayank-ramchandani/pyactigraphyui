export PATH="/opt/homebrew/bin:$PATH"
export PATH="$PATH:/Users/LENOVO/Desktop/flutter/bin"


[ -f "/Users/LENOVO/.ghcup/env" ] && source "/Users/LENOVO/.ghcup/env" # ghcup-env
# >>> conda initialize >>>
# !! Contents within this block are managed by 'conda init' !!
__conda_setup="$('/Users/LENOVO/anaconda3/bin/conda' 'shell.zsh' 'hook' 2> /dev/null)"
if [ $? -eq 0 ]; then
    eval "$__conda_setup"
else
    if [ -f "/Users/LENOVO/anaconda3/etc/profile.d/conda.sh" ]; then
        . "/Users/LENOVO/anaconda3/etc/profile.d/conda.sh"
    else
        export PATH="/Users/LENOVO/anaconda3/bin:$PATH"
    fi
fi
unset __conda_setup
# <<< conda initialize <<<

export PATH="/opt/homebrew/opt/llvm/bin:$PATH"

# Increase the number of commands to remember in the history
HISTSIZE=1000
SAVEHIST=2000

# Avoid duplicate entries
setopt HIST_IGNORE_DUPS
setopt HIST_IGNORE_ALL_DUPS
setopt HIST_SAVE_NO_DUPS

# Share history between sessions
setopt SHARE_HISTORY

# Append to the history file, don't overwrite it
setopt APPEND_HISTORY

export PATH=/opt/homebrew/opt/llvm/bin:/Users/LENOVO/fsl/share/fsl/bin:/Users/LENOVO/fsl/share/fsl/bin:/Library/Frameworks/Python.framework/Versions/3.10/bin:/usr/local/bin:/System/Cryptexes/App/usr/bin:/usr/bin:/bin:/usr/sbin:/sbin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/local/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/bin:/var/run/com.apple.security.cryptexd/codex.system/bootstrap/usr/appleinternal/bin:/opt/X11/bin:/Library/Apple/usr/bin:/opt/homebrew/opt/llvm/bin:/Users/LENOVO/anaconda3/bin:/Users/LENOVO/anaconda3/condabin:/Users/LENOVO/fsl/share/fsl/bin:/Library/Frameworks/Python.framework/Versions/3.10/bin:/Users/LENOVO/Library/Application Support/JetBrains/Toolbox/scripts:/Users/LENOVO/Desktop/flutter/bin:/Users/LENOVO/Library/Application Support/JetBrains/Toolbox/scripts:/Users/LENOVO/Desktop/flutter/bin:/opt/homebrew/bin:/opt/homebrew/bin
