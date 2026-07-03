import type { Variants } from 'framer-motion';

export const motionVariants = {
  pageTransition: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] }
  },

  hoverLift: {
    whileHover: { y: -2, boxShadow: '0 4px 12px rgba(0,0,0,0.1)' },
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] }
  },

  modalOpen: {
    initial: { opacity: 0, scale: 0.95 },
    animate: { opacity: 1, scale: 1 },
    exit: { opacity: 0, scale: 0.95 },
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] }
  },

  listStagger: {
    container: {
      animate: {
        transition: {
          staggerChildren: 0.05
        }
      }
    } as Variants,
    item: {
      initial: { opacity: 0, y: 10 },
      animate: { opacity: 1, y: 0 },
      transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] }
    }
  },

  fadeIn: {
    initial: { opacity: 0 },
    animate: { opacity: 1 },
    exit: { opacity: 0 },
    transition: { duration: 0.2, ease: [0.4, 0, 0.2, 1] }
  },

  slideUp: {
    initial: { opacity: 0, y: 20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: 20 },
    transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] }
  },

  slideDown: {
    initial: { opacity: 0, y: -20 },
    animate: { opacity: 1, y: 0 },
    exit: { opacity: 0, y: -20 },
    transition: { duration: 0.25, ease: [0.4, 0, 0.2, 1] }
  }
};

export const pageTransitionProps = {
  initial: motionVariants.pageTransition.initial,
  animate: motionVariants.pageTransition.animate,
  exit: motionVariants.pageTransition.exit,
  transition: motionVariants.pageTransition.transition
};
