package package_name

import std.collection.*
import std.io.*
import std.reflect.*
import std.random.*
import std.convert .*

// 要设置为主构函数，就加上注解：@Principal
@Annotation
public class Principal {
    const Principal() {}
}

public class SimpleIoc {
    // 用于存储类型与其构造函数的映射。是默认的构造函数。
    private let _constructorInfos = HashMap<TypeInfo, ConstructorInfo>()

    // 用于存储类型、名称和构造函数信息。是个性化的构造函数。
    private let _factories = HashMap<TypeInfo, HashMap<String, ConstructorInfo>>()

    // 用于存储类型、名称和对象实例。用于缓存创建的对象实例。
    private let _instancesRegistry = HashMap<TypeInfo, HashMap<String, Object>>()

    // 用于存储接口类型与其实现类的映射。用于实现接口到实现类的自动解析。
    private let _interfaceToClassMap = HashMap<TypeInfo, TypeInfo>()

    // 初始化为一个随机生成的GUID字符串。用于默认情况下的键值。
    private let _defaultKey = {
        random: Random => "${random.nextBits(32).format("x")}-${random.nextBits(16).format("x")}-${random.nextBits(16).format("x")}-${random.nextBits(16).format("x")}-${random.nextBits(48).format("x")}"
    }(Random())

    // 一个静态的私有 SimpleIoc 类型的字段，用于存储 SimpleIoc 类的默认实例。
    private static let _default: SimpleIoc = SimpleIoc()

    private init() {}

    public static prop default: SimpleIoc {
        get() {
            _default
        }
    }

    public func containsCreated<TClass>(): Bool {
        return containsCreated<TClass>("")
    }

    // 这个方法的目的是检查一个注册表（_instancesRegistry）中是否包含特定类型 T 的实例
    public func containsCreated<TClass>(key: String): Bool {
        let classType = TypeInfo.of<TClass>()

        if (!_instancesRegistry.contains(classType)) {
            return false
        }

        // 检查传入的 key 参数是否为空。如果是，那么接下来的检查将不基于 key，而是检查 TClass 类型是否有任何实例被注册。
        if (key.isEmpty()) {
            return _instancesRegistry[classType].size > 0
        }

        // 如果 key 不为空，这个方法将检查 TClass 类型在 _instancesRegistry 中注册的实例字典是否包含指定的 key。
        return _instancesRegistry[classType].contains(key)
    }

    public func isRegistered<TClass>(): Bool {
        let classType = TypeInfo.of<TClass>()
        return _interfaceToClassMap.contains(classType)
    }

    public func isRegistered<TClass>(key: String): Bool {
        let classType = TypeInfo.of<TClass>()
        if (!_interfaceToClassMap.contains(classType) || !_factories.contains(classType)) {
            return false
        }
        return _factories[classType].contains(key)
    }

    public func registerDerived<TInterface, TClass>(): Unit {
        registerDerived<TInterface, TClass>(false)
    }

    // 用与同时有接口和类的注册
    public func registerDerived<TInterface, TClass>(createInstanceImmediately: Bool): Unit {
        let interfaceType = TypeInfo.of<TInterface>()
        let classType = TypeInfo.of<TClass>()

        if (!classType.isSubtypeOf(interfaceType)) {
            if (let Some(value) <- (interfaceType as InterfaceTypeInfo)) {
                var found = false
                for (`interface` in classType.superInterfaces) {
                    if (`interface`.qualifiedName == value.qualifiedName) {
                        found = true
                        break
                    }
                }
                if (!found) {
                    throw Exception("TClass must implement TInterface")
                }
            } else {
                throw Exception("TClass must implement TInterface")
            }
        }

        if (_interfaceToClassMap.contains(interfaceType)) {
            if (_interfaceToClassMap[interfaceType] != classType) {
                throw Exception("Wrong TInterface/TClass")
            }
        } else {
            _interfaceToClassMap.add(interfaceType, classType)
            _constructorInfos.add(classType, GetConstructorInfo(classType))
        }

        let factory = getFactory(classType)
        Doregister(classType, factory, _defaultKey)

        if (createInstanceImmediately) {
            getInstance<TInterface>();
        }
    }

    public func registerDerived<TInterface, TClass>(factory: ConstructorInfo): Unit {
        registerDerived<TInterface, TClass>(factory, false)
    }

    // 用于指定构造函数的注册
    public func registerDerived<TInterface, TClass>(factory: ConstructorInfo, createInstanceImmediately: Bool): Unit {
        if (factory.toString().isEmpty()) {
            throw Exception("Missing parameter: factory")
        }

        let interfaceType = TypeInfo.of<TInterface>()
        let classType = TypeInfo.of<TClass>()

        if (_factories.contains(classType) && _factories[classType].contains(_defaultKey)) {
            throw Exception("There is already a factory registered")
        }

        if (_interfaceToClassMap.contains(interfaceType)) {
            if (_interfaceToClassMap[interfaceType] != classType) {
                throw Exception("Wrong TInterface/TClass")
            }
        } else {
            _interfaceToClassMap.add(interfaceType, classType)
        }

        Doregister(classType, factory, _defaultKey)

        if (createInstanceImmediately) {
            getInstance<TInterface>();
        }
    }

    public func registerDerived<TInterface, TClass>(factory: ConstructorInfo, key: String) {
        registerDerived<TInterface, TClass>(factory, key, false)
    }

    // 用于指定构造函数和key的注册
    public func registerDerived<TInterface, TClass>(factory: ConstructorInfo, key: String,
        createInstanceImmediately: Bool): Unit {
        if (factory.toString().isEmpty()) {
            throw Exception("Missing parameter: factory")
        }

        let interfaceType = TypeInfo.of<TInterface>()
        let classType = TypeInfo.of<TClass>()

        if (_factories.contains(classType) && _factories[classType].contains(key)) {
            throw Exception("There is already a factory registered with key: ${key}")
        }

        if (_interfaceToClassMap.contains(interfaceType)) {
            if (_interfaceToClassMap[interfaceType] != classType) {
                throw Exception("Wrong TInterface/TClass")
            }
        } else {
            _interfaceToClassMap.add(interfaceType, classType)
        }

        Doregister(classType, factory, key)

        if (createInstanceImmediately) {
            getInstance<TInterface>(key);
        }
    }

    public func register<TClass>(): Unit where TClass <: Object {
        register<TClass>(false)
    }

    // 用于只有类的注册
    public func register<TClass>(createInstanceImmediately: Bool): Unit where TClass <: Object {
        let classType = TypeInfo.of<TClass>()

        if ((classType as ClassTypeInfo).getOrThrow().isAbstract()) {
            throw Exception("An interface cannot be registered alone")
        }

        if (_factories.contains(classType) && _factories[classType].contains(_defaultKey)) {
            if (!_constructorInfos.contains(classType)) {
                throw Exception("Class is already registered")
            }
            return
        }

        if (!_interfaceToClassMap.contains(classType)) {
            _interfaceToClassMap.add(classType, classType)
        }

        _constructorInfos.add(classType, GetConstructorInfo(classType))

        let factory = getFactory(classType)
        Doregister(classType, factory, _defaultKey)

        if (createInstanceImmediately) {
            getInstance<TClass>();
        }
    }

    public func register<TClass>(factory: ConstructorInfo): Unit where TClass <: Object {
        register<TClass>(factory, false)
    }

    // 用于指定构造函数的注册
    public func register<TClass>(factory: ConstructorInfo, createInstanceImmediately: Bool): Unit where TClass <: Object {
        if (factory.toString().isEmpty()) {
            throw Exception("Missing parameter: factory")
        }

        let classType = TypeInfo.of<TClass>()

        if (_factories.contains(classType) && _factories[classType].contains(_defaultKey)) {
            throw Exception("There is already a factory registered")
        }

        if (!_interfaceToClassMap.contains(classType)) {
            _interfaceToClassMap.add(classType, classType)
        }

        Doregister(classType, factory, _defaultKey)

        if (createInstanceImmediately) {
            getInstance<TClass>();
        }
    }

    public func register<TClass>(factory: ConstructorInfo, key: String) where TClass <: Object {
        register<TClass>(factory, key, false)
    }

    // 用于指定构造函数和key的注册
    public func register<TClass>(factory: ConstructorInfo, key: String, createInstanceImmediately: Bool): Unit where TClass <: Object {
        if (factory.toString().isEmpty()) {
            throw Exception("Missing parameter: factory")
        }

        let classType = TypeInfo.of<TClass>()

        if (_factories.contains(classType) && _factories[classType].contains(key)) {
            throw Exception("There is already a factory registered with key: ${key}")
        }

        if (!_interfaceToClassMap.contains(classType)) {
            _interfaceToClassMap.add(classType, classType)
        }

        Doregister(classType, factory, key)

        if (createInstanceImmediately) {
            getInstance<TClass>(key);
        }
    }

    // 用于从SimpleIoc容器中注销一个类型
    public func unregister<TClass>(): Unit {
        let serviceType = TypeInfo.of<TClass>()
        let resolveTo: TypeInfo

        if (_interfaceToClassMap.contains(serviceType)) {
            if (_interfaceToClassMap[serviceType].name != serviceType.name) {
                resolveTo = serviceType
            } else {
                resolveTo = _interfaceToClassMap[serviceType]
            }
        } else {
            resolveTo = serviceType
        }

        if (_instancesRegistry.contains(serviceType)) {
            _instancesRegistry.remove(serviceType)
        }
        if (_interfaceToClassMap.contains(serviceType)) {
            _interfaceToClassMap.remove(serviceType)
        }
        if (_factories.contains(serviceType)) {
            _factories.remove(serviceType)
        }
        if (_constructorInfos.contains(resolveTo)) {
            _constructorInfos.remove(resolveTo)
        }
    }

    // 从容器中移除特定的实例
    public func unregister<TClass>(instance: TClass) {
        let classType = TypeInfo.of<TClass>()

        if (_instancesRegistry.contains(classType)) {
            let keys: ArrayList<String> = ArrayList<String>()

            for ((key, value) in _instancesRegistry[classType]) {
                if (refEq(value, (instance as Object).getOrThrow())) {
                    keys.add(key)
                }
            }

            for (index in 0..keys.size) {
                let key = keys[index]
                _instancesRegistry[classType].remove(key)
            }
        }
    }

    // 用于从SimpleIoc容器中注销特定类型和键的注册
    public func unregister<TClass>(key: String) {
        let classType = TypeInfo.of<TClass>()

        if (_instancesRegistry.contains(classType)) {
            let keys: ArrayList<String> = ArrayList<String>()
            for ((mykey, value) in _instancesRegistry[classType]) {
                if (mykey == key) {
                    keys.add(mykey)
                }
            }

            for (index in 0..keys.size) {
                let key = keys[index]
                _instancesRegistry[classType].remove(key)
            }
        }

        if (_factories.contains(classType)) {
            if (_factories[classType].contains(key)) {
                _factories[classType].remove(key)
            }
        }
    }

    public func reset() {
        _interfaceToClassMap.clear()
        _instancesRegistry.clear()
        _constructorInfos.clear()
        _factories.clear()
    }

    // 用于获取工厂函数
    public func getFactory(classType: TypeInfo): ConstructorInfo {
        let constructor = if (_constructorInfos.contains(classType)) {
            _constructorInfos[classType]
        } else {
            GetConstructorInfo(classType)
        }
        return constructor
    }

    public func construct<TClass>(): TClass where TClass <: Object {
        let instance = makeInstanceForType(TypeInfo.of<TClass>(), 0, HashSet<TypeInfo>())
        return (instance as TClass).getOrThrow()
    }

    public func construct(classType: TypeInfo): Object {
        return makeInstanceForType(classType, 0, HashSet<TypeInfo>())
    }

    private static func getPreferredConstructorInfo(constructorInfos: ArrayList<ConstructorInfo>): ConstructorInfo {
        var preferredConstructorInfo: ConstructorInfo = constructorInfos.toArray()[0]
        let preferredConstructorInfoFlag = false

        // 找出主构函数
        for (constructorInfo in constructorInfos) {
            if (constructorInfo.findAnnotation<Principal>().isSome()) {
                preferredConstructorInfo = constructorInfo
                return preferredConstructorInfo
            }
        }

        // 找不到就报错
        if (!preferredConstructorInfoFlag) {
            throw Exception("Cannot register: Multiple constructors found but none marked with @Principal.")
        }

        return preferredConstructorInfo
    }

    // 用于获取构造函数信息
    public func GetConstructorInfo(classType: TypeInfo): ConstructorInfo {
        let resolveTo: TypeInfo

        if (_interfaceToClassMap.contains(classType)) {
            if (_interfaceToClassMap[classType].name != classType.name) {
                resolveTo = classType
            } else {
                resolveTo = _interfaceToClassMap[classType]
            }
        } else {
            resolveTo = classType
        }

        let constructorInfos = ((resolveTo as ClassTypeInfo).getOrThrow()).constructors

        if (constructorInfos.size > 1) {
            return getPreferredConstructorInfo(ArrayList(constructorInfos))
        }

        if (constructorInfos.size == 0) {
            throw Exception("Cannot register: No public constructor found")
        }
        return constructorInfos.toArray()[0]
    }

    // 用于调用doGetService，形成递归
    public func getService(serviceType: TypeInfo): Object {
        return doGetService(serviceType, _defaultKey)
    }

    // 用于绑定serviceType，factory，key
    private func Doregister(classType: TypeInfo, factory: ConstructorInfo, key: String): Unit {
        if (_factories.contains(classType)) {
            if (_factories[classType].contains(key)) {
                return
            } else {
                _factories[classType].add(key, factory)
            }
        } else {
            let factories = HashMap<String, ConstructorInfo>()
            factories.add(key, factory)
            _factories.add(classType, factories)
        }
    }

    // 用于获取递归过程中的实例
    public func doGetService(serviceType: TypeInfo, key: String, cache!: Bool = true): Object {
        var serviceKey = key
        if (key.isEmpty()) {
            serviceKey = _defaultKey
        }

        var instances = HashMap<String, Object>()
        var instancesFlag: Bool = false

        if (!_instancesRegistry.contains(serviceType)) {
            if (!_interfaceToClassMap.contains(serviceType)) {
                throw Exception("Type not found in cache")
            }

            if (cache) {
                instances = HashMap<String, Object>()
                instancesFlag = true
                _instancesRegistry.add(serviceType, instances)
            }
        } else {
            instances = _instancesRegistry[serviceType]
            instancesFlag = true
        }

        if (instancesFlag && instances.contains(serviceKey)) {
            return instances[serviceKey]
        }

        var instance = Object()

        if (_interfaceToClassMap.contains(serviceType)) {
            let classType: TypeInfo = _interfaceToClassMap[serviceType]

            if (_factories.contains(classType)) {
                if (_factories[classType].contains(serviceKey)) {
                    let myfactory = _factories[classType][serviceKey]
                    instance = makeInstance(myfactory)
                } else {
                    if (_factories[classType].contains(_defaultKey)) {
                        let myfactory = _factories[classType][_defaultKey]
                        instance = makeInstance(myfactory)
                    } else {
                        throw Exception("Type not found in cache without a key")
                    }
                }
            }
        }

        if (instancesFlag && cache) {
            _instancesRegistry[serviceType].add(serviceKey, instance)
        }
        return instance
    }

    private static func isNamed(typeInfo: TypeInfo, name: String): Bool {
        return typeInfo.name == name || typeInfo.qualifiedName == name
    }

    private static func isAnyName(typeInfo: TypeInfo): Bool {
        return isNamed(typeInfo, "Any") || isNamed(typeInfo, "Interface-Any") || isNamed(typeInfo, "std.core.Any")
    }

    private static func isObjectName(typeInfo: TypeInfo): Bool {
        return isNamed(typeInfo, "Object") || isNamed(typeInfo, "Class-Object") || isNamed(typeInfo, "std.core.Object")
    }

    private static func isStringName(typeInfo: TypeInfo): Bool {
        return isNamed(typeInfo, "String") || isNamed(typeInfo, "Struct-String") || isNamed(typeInfo, "std.core.String")
    }

    private static func isOutputStreamName(typeInfo: TypeInfo): Bool {
        return isNamed(typeInfo, "OutputStream") || isNamed(typeInfo, "std.io.OutputStream")
    }

    private static func isInputStreamName(typeInfo: TypeInfo): Bool {
        return isNamed(typeInfo, "InputStream") || isNamed(typeInfo, "std.io.InputStream")
    }

    private static func isSeekableName(typeInfo: TypeInfo): Bool {
        return isNamed(typeInfo, "Seekable") || isNamed(typeInfo, "std.io.Seekable")
    }

    private func makeDefaultValue(typeInfo: TypeInfo, depth: Int64, constructing: HashSet<TypeInfo>): Any {
        if (isAnyName(typeInfo) || isObjectName(typeInfo)) {
            return Object()
        }
        if (isStringName(typeInfo)) {
            return ""
        }
        if (isNamed(typeInfo, "Bool") || isNamed(typeInfo, "std.core.Bool")) {
            return false
        }
        if (isNamed(typeInfo, "Rune") || isNamed(typeInfo, "std.core.Rune")) {
            return Rune(0)
        }
        if (isNamed(typeInfo, "Int64") || isNamed(typeInfo, "std.core.Int64")) {
            return Int64(0)
        }
        if (isNamed(typeInfo, "Int32") || isNamed(typeInfo, "std.core.Int32")) {
            return Int32(0)
        }
        if (isNamed(typeInfo, "Int16") || isNamed(typeInfo, "std.core.Int16")) {
            return Int16(0)
        }
        if (isNamed(typeInfo, "Int8") || isNamed(typeInfo, "std.core.Int8")) {
            return Int8(0)
        }
        if (isNamed(typeInfo, "UInt64") || isNamed(typeInfo, "std.core.UInt64")) {
            return UInt64(0)
        }
        if (isNamed(typeInfo, "UInt32") || isNamed(typeInfo, "std.core.UInt32")) {
            return UInt32(0)
        }
        if (isNamed(typeInfo, "UInt16") || isNamed(typeInfo, "std.core.UInt16")) {
            return UInt16(0)
        }
        if (isNamed(typeInfo, "UInt8") || isNamed(typeInfo, "std.core.UInt8")) {
            return UInt8(0)
        }
        if (isNamed(typeInfo, "Float64") || isNamed(typeInfo, "std.core.Float64")) {
            return Float64(0.0)
        }
        if (isNamed(typeInfo, "Float32") || isNamed(typeInfo, "std.core.Float32")) {
            return Float32(0.0)
        }
        if (isNamed(typeInfo, "StringBuilder") || isNamed(typeInfo, "std.core.StringBuilder")) {
            return StringBuilder()
        }
        if (isOutputStreamName(typeInfo) || isInputStreamName(typeInfo) || isSeekableName(typeInfo) || isNamed(typeInfo, "ByteBuffer") || isNamed(typeInfo, "std.io.ByteBuffer")) {
            return ByteBuffer()
        }

        if (let Some(_) <- (typeInfo as InterfaceTypeInfo)) {
            throw Exception("mock ioc unsupported constructor parameter: interface ${typeInfo.qualifiedName}")
        }

        if (let Some(classInfo) <- (typeInfo as ClassTypeInfo)) {
            if (classInfo.isAbstract()) {
                throw Exception("mock ioc unsupported constructor parameter: abstract class ${typeInfo.qualifiedName}")
            }
            return makeInstanceForType(typeInfo, depth, constructing)
        }

        throw Exception("mock ioc unsupported constructor parameter: ${typeInfo.qualifiedName}")
    }

    private func makeInstanceForType(classType: TypeInfo, depth: Int64, constructing: HashSet<TypeInfo>): Object {
        if (depth > 4) {
            throw Exception("mock ioc unsupported constructor: recursion depth exceeded for ${classType.qualifiedName}")
        }
        if (constructing.contains(classType)) {
            throw Exception("mock ioc unsupported constructor: recursive dependency for ${classType.qualifiedName}")
        }

        let classInfo = (classType as ClassTypeInfo).getOrThrow()
        if (classInfo.isAbstract()) {
            throw Exception("mock ioc unsupported constructor: abstract class ${classType.qualifiedName}")
        }

        let constructors = classInfo.constructors.toArray()
        if (constructors.isEmpty()) {
            throw Exception("mock ioc unsupported constructor: no public constructor for ${classType.qualifiedName}")
        }

        constructing.add(classType)

        for (constructorInfo in constructors) {
            if (constructorInfo.parameters.isEmpty()) {
                try {
                    let instance = makeInstance(constructorInfo, depth, constructing)
                    constructing.remove(classType)
                    return instance
                } catch (e: Exception) {
                }
            }
        }

        for (constructorInfo in constructors) {
            if (constructorInfo.findAnnotation<Principal>().isSome()) {
                try {
                    let instance = makeInstance(constructorInfo, depth, constructing)
                    constructing.remove(classType)
                    return instance
                } catch (e: Exception) {
                }
            }
        }

        var maxParameterCount = 0
        for (constructorInfo in constructors) {
            if (constructorInfo.parameters.size > maxParameterCount) {
                maxParameterCount = constructorInfo.parameters.size
            }
        }

        for (parameterCount in 1..(maxParameterCount + 1)) {
            for (constructorInfo in constructors) {
                if (constructorInfo.parameters.size == parameterCount) {
                    try {
                        let instance = makeInstance(constructorInfo, depth, constructing)
                        constructing.remove(classType)
                        return instance
                    } catch (e: Exception) {
                    }
                }
            }
        }

        constructing.remove(classType)
        throw Exception("mock ioc unsupported constructor: no constructible public constructor for ${classType.qualifiedName}")
    }

    // 用于获取一个实例，过程中会递归调用getService来获取参数的实例
    private func makeInstance(myfactory: ConstructorInfo): Object {
        return makeInstance(myfactory, 0, HashSet<TypeInfo>())
    }

    private func makeInstance(myfactory: ConstructorInfo, depth: Int64, constructing: HashSet<TypeInfo>): Object {
        var instance = Object()
        let parameterInfos = myfactory.parameters
        let parameters: Array<Any> = Array<Any>(parameterInfos.size, repeat: Object())

        if (parameterInfos.size == 0) {
            let _emptyArguments = Array<Any>()
            instance = (myfactory.apply(_emptyArguments) as Object).getOrThrow()
        } else {
            for (parameterInfo in parameterInfos) {
                parameters[parameterInfo.index] = makeDefaultValue(parameterInfo.typeInfo, depth + 1, constructing)
            }
            instance = (myfactory.apply(parameters) as Object).getOrThrow()
        }

        return instance
    }

    // 用于获取所有已创建的实例
    public func getAllCreatedInstances(serviceType: TypeInfo): ArrayList<Object> {
        if (_instancesRegistry.contains(serviceType)) {
            (_instancesRegistry[serviceType].values as ArrayList<Object>).getOrThrow()
        }

        return ArrayList<Object>()
    }

    // 用于获取指定类型 TService 的所有已创建实例
    public func getAllCreatedInstances<TService>(): ArrayList<TService> {
        let serviceType = TypeInfo.of<TService>()
        // 调用非泛型版本的 getAllCreatedInstances 方法
        let tempArrayList: ArrayList<Object> = getAllCreatedInstances(serviceType)

        let myArrayList: ArrayList<TService> = ArrayList<TService>()
        for (index in 0..tempArrayList.size) {
            let tempItem = (tempArrayList[index] as TService).getOrThrow()
            myArrayList.add(tempItem, at: index)
        }

        return myArrayList
    }

    // 用于获取指定服务类型的所有实例
    public func getAllInstances(serviceType: TypeInfo): ArrayList<Object> {
        if (_factories.contains(serviceType)) {
            println("调用工厂方法")
            for (key in _factories[serviceType].keys()) {
                // 对每个工厂方法，调用 getInstance 方法来创建或获取实例
                getInstance(serviceType, key)
            }
        } else if (_interfaceToClassMap.contains(serviceType) && serviceType.name != _interfaceToClassMap[serviceType]
            .name) {
            println("进入elseif")
            // 如果serviceType是接口，就会执行下面语句
            let classType = _interfaceToClassMap[serviceType]
            // 对每个工厂方法，调用 getInstance 方法来创建或获取实例
            for (key in _factories[classType].keys()) {
                println("进入for： " + key)
                getInstance(serviceType, key)
            }
        }

        if (_instancesRegistry.contains(serviceType)) {
            // 如果包含，则返回该类型对应的所有实例（存储在字典的值中）
            return ArrayList(_instancesRegistry[serviceType].values())
        }

        return ArrayList<Object>()
    }

    // 获取所有注册的 TService 类型的实例
    public func getAllInstances<TService>(): ArrayList<TService> {
        let tempArrayList: ArrayList<Object> = getAllInstances(TypeInfo.of<TService>())
        let myArrayList: ArrayList<TService> = ArrayList<TService>()

        // 将返回的对象集合中的每个实例转换为 TService 类型。
        for (index in 0..tempArrayList.size) {
            let tempItem = (tempArrayList[index] as TService).getOrThrow()
            myArrayList.add(tempItem)
        }

        return myArrayList
    }

    // 获取指定类型的实例。如果之前没有创建过实例，会创建一个新实例并缓存。
    public func getInstance(serviceType: TypeInfo): Object {
        return doGetService(serviceType, _defaultKey)
    }

    // 获取指定类型的新实例，但不会缓存。每次调用都会返回一个新的实例。
    public func getInstanceWithoutCaching(serviceType: TypeInfo): Object {
        return doGetService(serviceType, _defaultKey, cache: false)
    }

    // 根据指定的类型和键获取实例。如果该键对应的实例不存在，会创建一个新实例并缓存。
    public func getInstance(serviceType: TypeInfo, key: String): Object {
        return doGetService(serviceType, key)
    }

    // 根据指定的类型和键获取新实例，但不会缓存。
    public func getInstanceWithoutCaching(serviceType: TypeInfo, key: String): Object {
        return doGetService(serviceType, key, cache: false)
    }

    // 获取指定泛型类型的实例。如果之前没有创建过实例，会创建一个新实例并缓存。
    public func getInstance<TService>(): TService {
        let instance = doGetService(TypeInfo.of<TService>(), _defaultKey)
        return (instance as TService).getOrThrow()
    }

    // 获取指定泛型类型的新实例，但不会缓存。
    public func getInstanceWithoutCaching<TService>(): TService {
        let instance = doGetService(TypeInfo.of<TService>(), _defaultKey, cache: false)
        return (instance as TService).getOrThrow()
    }

    // 根据指定的泛型类型和键获取实例。如果该键对应的实例不存在，会创建一个新实例并缓存。
    public func getInstance<TService>(key: String): TService {
        let instance = doGetService(TypeInfo.of<TService>(), key)
        return (instance as TService).getOrThrow()
    }

    // 根据指定的泛型类型和键获取新实例，但不会缓存。
    public func getInstanceWithoutCaching<TService>(key: String): TService {
        let instance = doGetService(TypeInfo.of<TService>(), key, cache: false)
        return (instance as TService).getOrThrow()
    }
}
