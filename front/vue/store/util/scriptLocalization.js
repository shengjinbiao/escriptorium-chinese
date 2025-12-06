const zhHantScriptTranslations = {
    "Han (Hanzi, Kanji, Hanja)": "漢字",
    "Han (Hanzi, Kanji, Hanja) vertical": "漢字（直排）",
    "Han (Simplified variant)": "汉字（简体）",
    "Han (Traditional variant)": "漢字（繁體）",
    "Han with Bopomofo (alias for Han + Bopomofo)": "漢字＋注音符號",
    Bopomofo: "注音符號",
};

export function localizeScriptName(name) {
    if (!name) {
        return "";
    }

    return zhHantScriptTranslations[name] || name;
}

export default localizeScriptName;
