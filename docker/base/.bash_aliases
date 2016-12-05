

function proml {
  local        BLUE="\[\033[0;34m\]"
  local         RED="\[\033[0;31m\]"
  local   LIGHT_RED="\[\033[1;31m\]"
  local  PURPLE="\[\033[0;35m\]"
  local  LIGHT_BLUE="\[\033[0;36m\]"
  local  WHITE="\[\033[0;37m\]"
  case $TERM in
    xterm*)
    TITLEBAR='\[\033]0;\W\007\]'
    ;;
    *)
    TITLEBAR=""
    ;;
  esac

PS1="${TITLEBAR}\
$WHITE\u@\h:\W$LIGHT_BLUE(\$(echo $SERVICES_ENVIRONMENT))\
$WHITE\$ "
}
proml
