"use client";

import { createContext, useCallback, useContext, useEffect, useMemo, useState } from "react";
import ko from "@/lib/locales/ko.json";
import en from "@/lib/locales/en.json";

export const SUPPORTED_LOCALES = [
  "ko", "en", "ar", "bg", "bo", "ca", "ckb", "cs", "da", "de",
  "el", "eo", "es", "et", "fa", "fi", "fr", "he", "hr", "hu",
  "id", "it", "ja", "ka", "kk", "lt", "nl", "no", "nqo", "pl",
  "pt", "pt-BR", "ro", "ru", "rue", "sk", "sl", "sq", "sr", "sv",
  "ta", "th", "tl", "tr", "uk", "vi", "zh-CHT", "zh-CN",
] as const;

export type Locale = (typeof SUPPORTED_LOCALES)[number];

export const LOCALE_NAMES: Record<string, string> = {
  ko: "한국어", en: "English", ar: "العربية", bg: "Български", bo: "བོད་སྐད",
  ca: "Català", ckb: "کوردی", cs: "Čeština", da: "Dansk", de: "Deutsch",
  el: "Ελληνικά", eo: "Esperanto", es: "Español", et: "Eesti", fa: "فارسی",
  fi: "Suomi", fr: "Français", he: "עברית", hr: "Hrvatski", hu: "Magyar",
  id: "Bahasa Indonesia", it: "Italiano", ja: "日本語", ka: "ქართული", kk: "Қазақша",
  lt: "Lietuvių", nl: "Nederlands", no: "Norsk", nqo: "ߒߞߏ", pl: "Polski",
  pt: "Português", "pt-BR": "Português (BR)", ro: "Română", ru: "Русский",
  rue: "Русиньскый", sk: "Slovenčina", sl: "Slovenščina", sq: "Shqip",
  sr: "Српски", sv: "Svenska", ta: "தமிழ்", th: "ไทย", tl: "Tagalog",
  tr: "Türkçe", uk: "Українська", vi: "Tiếng Việt", "zh-CHT": "繁體中文", "zh-CN": "简体中文",
};

type Messages = Record<string, Record<string, string>>;

const bundled: Record<string, Messages> = { ko, en };

async function loadMessages(locale: string): Promise<Messages> {
  if (bundled[locale]) return bundled[locale];
  try {
    const mod = await import(`@/lib/locales/${locale}.json`);
    return mod.default;
  } catch {
    return ko;
  }
}

function getValue(messages: Messages, key: string): string {
  const [ns, k] = key.split(".");
  if (ns && k) return messages[ns]?.[k] ?? "";
  return "";
}

interface I18nContextValue {
  locale: string;
  setLocale: (locale: string) => void;
  t: (key: string) => string;
}

const I18nContext = createContext<I18nContextValue>({
  locale: "ko",
  setLocale: () => {},
  t: (key) => key,
});

export function useTranslation() {
  return useContext(I18nContext);
}

export function I18nProvider({ children }: { children: React.ReactNode }) {
  const [locale, setLocaleRaw] = useState("ko");
  const [messages, setMessages] = useState<Messages>(ko);
  const [ready, setReady] = useState(false);

  // Load saved locale on mount
  useEffect(() => {
    const saved = typeof window !== "undefined" ? localStorage.getItem("ui2psd_locale") : null;
    const target = saved && SUPPORTED_LOCALES.includes(saved as Locale) ? saved : "ko";
    setLocaleRaw(target);
    loadMessages(target).then((m) => {
      setMessages(m);
      setReady(true);
    });
  }, []);

  const setLocale = useCallback((newLocale: string) => {
    setLocaleRaw(newLocale);
    localStorage.setItem("ui2psd_locale", newLocale);
    loadMessages(newLocale).then(setMessages);
  }, []);

  // t function recalculated when messages change
  const t = useMemo(() => {
    return (key: string): string => {
      const val = getValue(messages, key);
      if (val) return val;
      return getValue(ko as Messages, key) || key;
    };
  }, [messages]);

  if (!ready) return null;

  return (
    <I18nContext.Provider value={{ locale, setLocale, t }}>
      {children}
    </I18nContext.Provider>
  );
}
