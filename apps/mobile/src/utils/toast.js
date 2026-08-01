import Toast from 'react-native-root-toast';

let currentToast = null;

export const showToast = (message, isError = false) => {
  if (currentToast) {
    Toast.hide(currentToast);
  }
  
  currentToast = Toast.show(message, {
    duration: Toast.durations.LONG,
    position: Toast.positions.BOTTOM,
    shadow: true,
    animation: true,
    hideOnPress: true,
    backgroundColor: isError ? '#EF4444' : '#10B981',
    textColor: '#FFFFFF',
    opacity: 1,
  });
};
