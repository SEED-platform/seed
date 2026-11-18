export class AnimationCurves {
  static standard = 'cubic-bezier(0.4, 0.0, 0.2, 1)'
  static deceleration = 'cubic-bezier(0.0, 0.0, 0.2, 1)'
  static acceleration = 'cubic-bezier(0.4, 0.0, 1, 1)'
  static sharp = 'cubic-bezier(0.4, 0.0, 0.6, 1)'
}

export class AnimationDurations {
  static readonly slow = '375ms'
  static readonly entering = '225ms'
  static readonly exiting = '195ms'
}
