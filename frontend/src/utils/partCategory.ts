/**
 * What a FitGirl part is for, from its file name. The selective filter uses this to skip
 * voice packs and extras, and the tour's sample game is built to exercise it.
 */

export type PartCategory = 'core' | 'language' | 'optional';

export function classifyPart(filename: string): PartCategory {
  const name = (filename || '').toLowerCase();
  // English is treated as part of the game for English users.
  if (name.includes('fg-selective-english') || name.includes('selective-english')) return 'core';
  if (name.includes('fg-selective-') || name.includes('selective-')) return 'language';
  if (name.includes('fg-optional-') || name.includes('optional-') || name.includes('soundtrack') || name.includes('bonus')) {
    return 'optional';
  }
  return 'core';
}
