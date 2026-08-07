package package_name

import std.collection.*
import std.io.*

public func __mockCreateViaIoc<T>(): T where T <: Object {
    SimpleIoc.default.unregister<T>()
    let instance = SimpleIoc.default.construct<T>()
    SimpleIoc.default.unregister<T>()
    instance
}

public func __mockArrayListOf<T>(items: Array<T>): ArrayList<T> {
    let list = ArrayList<T>(items.size)
    list.add(all: items)
    list
}

public func __mockResetArrayList<T>(target: ArrayList<T>, items: Array<T>): Unit {
    target.clear()
    target.add(all: items)
}

public func __mockHashSetOf<T>(items: Array<T>): HashSet<T> where T <: Hashable & Equatable<T> {
    let set = HashSet<T>()
    for (item in items) {
        set.add(item)
    }
    set
}

public func __mockResetHashSet<T>(target: HashSet<T>, items: Array<T>): Unit where T <: Hashable & Equatable<T> {
    target.clear()
    for (item in items) {
        target.add(item)
    }
}

public func __mockHashMapOf<K, V>(items: Array<(K, V)>): HashMap<K, V> where K <: Hashable & Equatable<K> {
    let map = HashMap<K, V>()
    for ((k, v) in items) {
        map.add(k, v)
    }
    map
}

public func __mockResetHashMap<K, V>(target: HashMap<K, V>, items: Array<(K, V)>): Unit where K <: Hashable & Equatable<K> {
    target.clear()
    for ((k, v) in items) {
        target.add(k, v)
    }
}

public func __mockByteBufferOf(items: Array<UInt8>): ByteBuffer {
    let stream = ByteBuffer()
    stream.write(items)
    stream.seek(SeekPosition.Begin(0))
    stream
}

public func __mockResetByteBuffer(target: ByteBuffer, items: Array<UInt8>): Unit {
    target.clear()
    target.write(items)
    target.seek(SeekPosition.Begin(0))
}

public func __mockStringReaderOf(text: String): StringReader<ByteBuffer> {
    let stream = ByteBuffer()
    stream.write(text.toArray())
    stream.seek(SeekPosition.Begin(0))
    StringReader(stream)
}

public func __mockStringWriterOf(text: String): StringWriter<ByteBuffer> {
    let stream = ByteBuffer()
    let writer = StringWriter(stream)
    writer.write(text)
    writer.flush()
    writer
}

public func __mockCharsetAlias(value: String): String {
    match (value) {
        case "UTF-8" => "utf-8"
        case "UTF8" => "utf-8"
        case "UTF-16" => "utf-16"
        case "UTF-16BE" => "utf-16-be"
        case "UTF-16LE" => "utf-16-le"
        case "US-ASCII" => "ascii"
        case "ISO-8859-1" => "latin1"
        case "windows-1252" => "cp1252"
        case "windows-1251" => "cp1251"
        case "Big5" => "big5"
        case "GB2312" => "gb2312"
        case "GB18030" => "gb18030"
        case "Shift_JIS" => "shift_jis"
        case "ISO-2022-JP" => "iso2022_jp"
        case other => other
    }
}

public func __mockLocaleAlias(value: String): String {
    match (value) {
        case "en" => "en_US"
        case "fr" => "fr_FR"
        case "de" => "de_DE"
        case "es" => "es_ES"
        case "it" => "it_IT"
        case "pt" => "pt_PT"
        case "zh" => "zh_CN"
        case "ja" => "ja_JP"
        case "ko" => "ko_KR"
        case "ru" => "ru_RU"
        case "ar" => "ar_EG"
        case "ar_EG" => "ar_EG"
        case "hi" => "hi_IN"
        case "hi_IN" => "hi_IN"
        case other => other
    }
}

public func __mockNormalizeStruct(value: String): String {
    __mockLocaleAlias(__mockCharsetAlias(value))
}

public func __mockStringEqual(lhs: String, rhs: String): Bool {
    lhs == rhs || __mockNormalizeStruct(lhs) == __mockNormalizeStruct(rhs)
}

public func __mockByteStreamEquals(stream: ByteBuffer, expected: Array<UInt8>): Bool {
    let pos = stream.position
    stream.seek(SeekPosition.Begin(0))
    let current = readToEnd(stream)
    stream.seek(SeekPosition.Begin(pos))
    current == expected
}

public func __mockReaderEquals<T>(reader: StringReader<T>, expected: String): Bool where T <: InputStream & Seekable {
    reader.seek(SeekPosition.Begin(0))
    let content = reader.readToEnd()
    content == expected
}

public func __mockWriterEquals(buf: ByteBuffer, expected: String): Bool {
    buf.seek(SeekPosition.Begin(0))
    let content = readToEnd(buf)
    content == expected.toArray()
}
