package runtime

import std.reflect.*

interface _AnyHashableBox <: Hashable & Equatable<_AnyHashableBox> {
    func unwrap(): Any
}

class _HashableBox<T> <: _AnyHashableBox where T <: Hashable & Equatable<T> {
    private let value: T

    public init(value: T) {
        this.value = value
    }

    public func unwrap(): Any {
        return value
    }

    public func hashCode(): Int64 {
        return value.hashCode()
    }

    public operator func ==(rhs: _AnyHashableBox): Bool {
        match (rhs) {
            case b: _HashableBox<T> => return this.value == b.value
            case _ => return false
        }
    }

    public operator func !=(rhs: _AnyHashableBox): Bool {
        return !(this == rhs)
    }
}

public struct AnyHashable <: Hashable & Equatable<AnyHashable> {
    private let box: _AnyHashableBox

    private init(box: _AnyHashableBox) {
        this.box = box
    }

    public init(value: AnyHashable) {
        this.box = value.box
    }

    public init(value: Any) {
        this.box = AnyHashable.makeBox(value)
    }

    public static func of<T>(value: T): AnyHashable where T <: Hashable & Equatable<T> {
        return AnyHashable(_HashableBox<T>(value))
    }

    public func unwrap(): Any {
        return box.unwrap()
    }

    public func hashCode(): Int64 {
        return box.hashCode()
    }

    public operator func ==(rhs: AnyHashable): Bool {
        return this.box == rhs.box
    }

    public operator func !=(rhs: AnyHashable): Bool {
        return !(this == rhs)
    }

    private static func makeBox(value: Any): _AnyHashableBox {
        match (value) {
            case v: AnyHashable => return v.box

            case v: Bool => return _HashableBox<Bool>(v)
            case v: Rune => return _HashableBox<Rune>(v)

            case v: Int8 => return _HashableBox<Int8>(v)
            case v: Int16 => return _HashableBox<Int16>(v)
            case v: Int32 => return _HashableBox<Int32>(v)
            case v: Int64 => return _HashableBox<Int64>(v)
            case v: IntNative => return _HashableBox<IntNative>(v)

            case v: UInt8 => return _HashableBox<UInt8>(v)
            case v: UInt16 => return _HashableBox<UInt16>(v)
            case v: UInt32 => return _HashableBox<UInt32>(v)
            case v: UInt64 => return _HashableBox<UInt64>(v)
            case v: UIntNative => return _HashableBox<UIntNative>(v)

            case v: Float16 => return _HashableBox<Float16>(v)
            case v: Float32 => return _HashableBox<Float32>(v)
            case v: Float64 => return _HashableBox<Float64>(v)

            case v: String => return _HashableBox<String>(v)

            case _ => throw IllegalArgumentException("Unsupported AnyHashable key type: ${TypeInfo.of(value).qualifiedName}. Use AnyHashable.of<T>(value) before erasing to Any, or add a concrete match case.")
        }
    }
}

public func hashable(value: Any): AnyHashable {
    return AnyHashable(value)
}

public func hashableTyped<T>(value: T): AnyHashable where T <: Hashable & Equatable<T> {
    return AnyHashable.of<T>(value)
}

public func unwrap(value: AnyHashable): Any {
    return value.unwrap()
}
