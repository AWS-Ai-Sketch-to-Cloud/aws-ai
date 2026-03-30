const loginIdPattern = /^[a-z0-9]+$/;
const allowedSpecialChars = "!@#$%^&*()-_=+[]{};:,.?/|";
const escapedAllowedSpecialChars = allowedSpecialChars.replace(/[\\^$*+?.()|[\]{}-]/g, "\\$&");
const specialCharPattern = new RegExp(`[${escapedAllowedSpecialChars}]`);
const allowedPasswordPattern = new RegExp(`^[A-Za-z\\d${escapedAllowedSpecialChars}]+$`);
const repeatedDigitPattern = /(\d)\1\1/;
const whitespacePattern = /\s/;

function hasSequentialDigits(value: string, minRun = 3): boolean {
  const digits = Array.from(value)
    .filter((char) => /\d/.test(char))
    .map(Number);

  if (digits.length < minRun) {
    return false;
  }

  let ascendingRun = 1;
  let descendingRun = 1;

  for (let index = 1; index < digits.length; index += 1) {
    const diff = digits[index] - digits[index - 1];
    ascendingRun = diff === 1 ? ascendingRun + 1 : 1;
    descendingRun = diff === -1 ? descendingRun + 1 : 1;

    if (ascendingRun >= minRun || descendingRun >= minRun) {
      return true;
    }
  }

  return false;
}

export function validateLoginId(loginId: string): string | null {
  if (!loginId.trim()) {
    return "아이디를 입력해 주세요.";
  }

  if (!loginIdPattern.test(loginId)) {
    return "아이디는 영문 소문자와 숫자만 사용할 수 있습니다.";
  }

  return null;
}

export function validatePassword(password: string): string | null {
  if (!password) {
    return "비밀번호를 입력해 주세요.";
  }

  if (whitespacePattern.test(password)) {
    return "비밀번호에는 공백을 사용할 수 없습니다.";
  }

  if (!allowedPasswordPattern.test(password)) {
    return "비밀번호 특수문자는 ! @ # $ % ^ & * ( ) - _ = + [ ] { } ; : , . ? / | 만 사용할 수 있습니다.";
  }

  if (password.length < 8 || password.length > 128) {
    return "비밀번호는 8자 이상 128자 이하로 입력해 주세요.";
  }

  const categoryCount = [
    /[A-Z]/.test(password),
    /[a-z]/.test(password),
    /\d/.test(password),
    specialCharPattern.test(password),
  ].filter(Boolean).length;

  if (categoryCount < 2) {
    return "비밀번호는 대문자, 소문자, 숫자, 특수문자 중 2종류 이상을 포함해야 합니다.";
  }

  if (repeatedDigitPattern.test(password)) {
    return "비밀번호에는 동일한 숫자 3자리를 연속으로 사용할 수 없습니다.";
  }

  if (hasSequentialDigits(password)) {
    return "비밀번호에는 연속된 숫자 3자리 이상을 사용할 수 없습니다.";
  }

  return null;
}
