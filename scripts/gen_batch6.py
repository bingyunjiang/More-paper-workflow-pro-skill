#!/usr/bin/env python3
"""Generate batch-6 knowledge graph nodes/edges from extraction results."""
try:
    from console_compat import configure_console_output

    configure_console_output()
except Exception:
    pass

import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description="Generate batch-6 knowledge graph nodes/edges from extraction results.")
parser.add_argument("--extract-results", type=Path, required=True)
parser.add_argument("--analyzer-input", type=Path, required=True)
parser.add_argument("--output", type=Path, required=True)
args = parser.parse_args()

with args.extract_results.open(encoding="utf-8") as f:
    extract = json.load(f)
with args.analyzer_input.open(encoding="utf-8") as f:
    analyzer_input = json.load(f)

import_data = analyzer_input.get('batchImportData', {})
results = extract['results']
nodes, edges = [], []
seen_node_ids, edges_set = set(), set()

file_descriptions = {
    'aieng-ui/backend/tests/test_agent_activity.py': '测试代理活动代理（Broker）的发布/订阅机制，包括广播、退订、订阅者计数、队列溢出处理，以及工具调用事件流',
    'aieng-ui/backend/tests/test_agent_context.py': '测试代理上下文端点，验证 CAD/CAE 包结构返回、缺少包时的处理以及运行时工具注册',
    'aieng-ui/backend/tests/test_agent_observation.py': '测试代理观测模块，包括预览、审批、拒绝后的观测状态，求解器就绪检查以及 CAE 工作流规划',
    'aieng-ui/backend/tests/test_ai_preprocessing.py': '测试 AI 预处理管线，包括几何上下文构建、FEA 设置映射、用户提示构建、指针解析和物料目录',
    'aieng-ui/backend/tests/test_app_factory_structure.py': '测试应用工厂保持轻量级组合结构，以及 OpenAPI schema 能正常构建',
    'aieng-ui/backend/tests/test_backend_logging.py': '测试后端日志配置，包括 RotatingFileHandler、异常日志写入、错误度量端点和 Critique 端点日志',
    'aieng-ui/backend/tests/test_brep_graph.py': '测试 B-Rep 图构建，包括拓扑指针、面角色推断、面邻接关系、标准部件上下文和瞬态摘要',
    'aieng-ui/backend/tests/test_cad_generation.py': '全面的 CAD 生成测试套件，涵盖 build123d 执行、特征图检测、参数编辑、增量建模、引用图像搜索、设计评审和标准部件',
    'aieng-ui/backend/tests/test_cad_observation.py': '测试 CAD 观测模块，包括几何缺失检测、CAD 生成后观测、STEP 导出证据、无效 JSON 处理和自纠正信号',
    'aieng-ui/backend/tests/test_contextual_chat.py': '测试上下文聊天功能，包括包缺失处理、拓扑包含、设置 YAML、仿真结果和设计目标上下文',
    'aieng-ui/backend/tests/test_contextual_chat_pointers.py': '测试上下文聊天指针功能，包括指针格式化、无效指针处理、失效映射标记和 CAE 映射状态',
    'aieng-ui/backend/tests/test_engineering_action_plan.py': '测试工程动作规划器，包括材料变更、目标设置、CAD 优化意图识别和网格参数提取',
    'aieng-ui/backend/tests/test_engineering_templates.py': '测试工程模板框架，包括模板列表、参数 schema、预览生成、草稿保存、设计目标采纳和 CAD 夹具生成',
    'aieng-ui/backend/tests/test_external_adapters.py': '测试外部适配器注册表，包括能力清单验证、审批要求、声明推进约束和存根执行器',
    'aieng-ui/backend/tests/test_geometry_providers.py': '测试几何提供者模块，包含螺栓模式检测、面角色分配、拓扑加载、邻接图和接口图、编辑影响分析和指针语法',
    'aieng-ui/backend/tests/test_honesty.py': '测试系统诚实性边界，验证所有声明边界非空',
    'aieng-ui/backend/tests/test_intent_planner.py': '测试意图规划器，包括约束提取、模板动作建议、求解器就绪检查、审批等待和动作执行',
    'aieng-ui/backend/tests/test_issue4_package_cache.py': '测试包缓存问题修复，验证构建代理上下文时只打开一次 ZIP 包',
    'aieng-ui/backend/tests/test_nodes_on_face.py': '测试面上节点计算，涵盖各种面法线方向、斜面和圆柱面、回退逻辑和包围盒过滤',
    'aieng-ui/backend/tests/test_optimization_artifacts.py': '测试优化工件保存，包括包写入、审计跟踪、schema 校验拒绝和设计分叉检测',
    'aieng-ui/backend/tests/test_persistence.py': '测试持久化层，包括设置保存、聊天消息验证、会话管理、SSE 事件发布和代理事件去重',
    'aieng-ui/backend/tests/test_review_support_packet.py': '测试评审支持包，包括只读预览、声明边界、目标比较、导出和快照比对',
    'aieng-ui/backend/tests/test_runtime_tools.py': '测试运行时工具注册，验证工程模板工具已注册且预览为只读',
    'aieng-ui/backend/tests/test_simulation_runner.py': '测试仿真运行器，包含节点集映射、CalculiX 输入文件构建、模拟执行、工具检查和提示处理',
    'aieng-ui/backend/tests/test_simulation_stream.py': '测试仿真流，包括 SSE 格式、流执行、项目/包缺失处理和进度事件',
    'aieng-ui/backend/tests/test_snapshots.py': '测试快照功能，包括单调序列号、清理策略、记录/恢复操作和空列表处理',
    'aieng-ui/backend/tests/test_structural_adapter.py': '测试结构适配器，包括能力清单验证、准备预览、求解器运行循环和结果提取诚实性'
}

file_tags_map = {
    'aieng-ui/backend/tests/test_agent_activity.py': ['agent_activity', 'broker', '事件流', 'pytest', '测试'],
    'aieng-ui/backend/tests/test_agent_context.py': ['agent_context', 'CAD/CAE', '端点测试', 'pytest', '测试'],
    'aieng-ui/backend/tests/test_agent_observation.py': ['agent_observation', '观测', '审批', 'CAE', '测试'],
    'aieng-ui/backend/tests/test_ai_preprocessing.py': ['AI预处理', 'FEA', '几何', '验证', '测试'],
    'aieng-ui/backend/tests/test_app_factory_structure.py': ['app_factory', '轻量级', 'OpenAPI', '结构', '测试'],
    'aieng-ui/backend/tests/test_backend_logging.py': ['日志', '错误度量', 'RotatingFile', 'pytest', '测试'],
    'aieng-ui/backend/tests/test_brep_graph.py': ['B-Rep', '拓扑', '面邻接', '标准部件', '测试'],
    'aieng-ui/backend/tests/test_cad_generation.py': ['CAD生成', 'build123d', '特征图', '参数编辑', '设计评审'],
    'aieng-ui/backend/tests/test_cad_observation.py': ['CAD观测', '几何', 'STEP', '自纠正', '测试'],
    'aieng-ui/backend/tests/test_contextual_chat.py': ['上下文聊天', '拓扑', '仿真', '设计目标', '测试'],
    'aieng-ui/backend/tests/test_contextual_chat_pointers.py': ['指针', '映射', 'CAE', '失效', '测试'],
    'aieng-ui/backend/tests/test_engineering_action_plan.py': ['动作规划', '意图', '材料', 'CAD优化', '测试'],
    'aieng-ui/backend/tests/test_engineering_templates.py': ['工程模板', '预览', '草稿', '设计目标', 'CAD夹具'],
    'aieng-ui/backend/tests/test_external_adapters.py': ['外部适配器', '能力清单', '审批', '注册表', '测试'],
    'aieng-ui/backend/tests/test_geometry_providers.py': ['几何提供者', '螺栓检测', '面角色', '邻接图', '指针语法'],
    'aieng-ui/backend/tests/test_honesty.py': ['诚实性', '声明边界', '安全', 'pytest', '测试'],
    'aieng-ui/backend/tests/test_intent_planner.py': ['意图规划', '约束', '模板', '求解器', '测试'],
    'aieng-ui/backend/tests/test_issue4_package_cache.py': ['包缓存', 'ZIP', '代理上下文', '性能', '测试'],
    'aieng-ui/backend/tests/test_nodes_on_face.py': ['面上节点', '法线', '包围盒', '圆柱面', '测试'],
    'aieng-ui/backend/tests/test_optimization_artifacts.py': ['优化工件', 'Schema校验', '审计', '设计分叉', '测试'],
    'aieng-ui/backend/tests/test_persistence.py': ['持久化', 'SSE', '会话', '消息', '测试'],
    'aieng-ui/backend/tests/test_review_support_packet.py': ['评审包', '声明边界', '导出', '快照比对', '测试'],
    'aieng-ui/backend/tests/test_runtime_tools.py': ['运行时工具', '工程模板', '只读', '注册', '测试'],
    'aieng-ui/backend/tests/test_simulation_runner.py': ['仿真', 'CalculiX', '节点集', '网格', '测试'],
    'aieng-ui/backend/tests/test_simulation_stream.py': ['仿真流', 'SSE', '进度', '流执行', '测试'],
    'aieng-ui/backend/tests/test_snapshots.py': ['快照', '序列号', '清理', '恢复', '测试'],
    'aieng-ui/backend/tests/test_structural_adapter.py': ['结构适配器', '能力清单', '求解器', 'FRD', '测试']
}

for f in results:
    path = f['path']
    total_lines = f['totalLines']
    funcs = f.get('functions', [])
    classes = f.get('classes', [])
    call_graph = f.get('callGraph', [])
    func_count = len(funcs)
    class_count = len(classes)
    complexity = 'complex' if total_lines > 1000 else 'medium' if total_lines > 200 else 'simple'
    file_node_id = 'file:' + path
    seen_node_ids.add(file_node_id)
    file_name = path.split('/')[-1]
    nodes.append({'id': file_node_id, 'type': 'file', 'name': file_name, 'filePath': path, 'summary': file_descriptions.get(path, '测试文件 ' + file_name), 'tags': file_tags_map.get(path, ['测试', 'pytest', 'python']), 'complexity': complexity})
    func_names_in_file = {fn['name'] for fn in funcs}
    for func in funcs:
        fn_name = func['name']
        fn_id = 'function:' + path + ':' + fn_name
        seen_node_ids.add(fn_id)
        fn_tags = ['测试', 'pytest', '自动化测试'] if fn_name.startswith('test_') else ['辅助函数', '工具函数']
        nodes.append({'id': fn_id, 'type': 'function', 'name': fn_name, 'summary': ('测试函数 ' if fn_name.startswith('test_') else '辅助函数 ') + fn_name, 'tags': fn_tags, 'startLine': func.get('startLine', 0), 'endLine': func.get('endLine', 0), 'params': func.get('params', [])})
        edge_id = 'contains:' + file_node_id + '->' + fn_id
        if edge_id not in edges_set:
            edges.append({'source': file_node_id, 'target': fn_id, 'type': 'contains', 'direction': 'forward', 'weight': 1})
            edges_set.add(edge_id)
    for cls in classes:
        cls_name = cls['name']
        cls_id = 'class:' + path + ':' + cls_name
        seen_node_ids.add(cls_id)
        nodes.append({'id': cls_id, 'type': 'class', 'name': cls_name, 'summary': '测试类 ' + cls_name, 'tags': ['测试类', 'pytest'], 'startLine': cls.get('startLine', 0), 'endLine': cls.get('endLine', 0)})
        edge_id = 'contains:' + file_node_id + '->' + cls_id
        if edge_id not in edges_set:
            edges.append({'source': file_node_id, 'target': cls_id, 'type': 'contains', 'direction': 'forward', 'weight': 1})
            edges_set.add(edge_id)
        for method in cls.get('methods', []):
            m_name = method['name']
            m_id = 'function:' + path + ':' + m_name
            if m_id not in seen_node_ids:
                seen_node_ids.add(m_id)
                nodes.append({'id': m_id, 'type': 'function', 'name': m_name, 'summary': '方法 ' + m_name, 'tags': ['方法', '测试'], 'startLine': method.get('startLine', 0), 'endLine': method.get('endLine', 0), 'params': method.get('params', [])})
            eid = 'contains:' + cls_id + '->' + m_id
            if eid not in edges_set:
                edges.append({'source': cls_id, 'target': m_id, 'type': 'contains', 'direction': 'forward', 'weight': 1})
                edges_set.add(eid)
    for call in call_graph:
        caller_name = call['caller']
        callee_name = call['callee']
        caller_id = 'function:' + path + ':' + caller_name
        callee_id = 'function:' + path + ':' + callee_name
        if callee_name in func_names_in_file:
            edge_id = 'calls:' + caller_id + '->' + callee_id + '@' + str(call['lineNumber'])
            if edge_id not in edges_set:
                edges.append({'source': caller_id, 'target': callee_id, 'type': 'calls', 'direction': 'forward', 'weight': 1, 'lineNumber': call['lineNumber']})
                edges_set.add(edge_id)

for file_path, imports in import_data.items():
    file_node_id = 'file:' + file_path
    for imp in imports:
        imp_id = 'file:' + imp
        edge_id = 'imports:' + file_node_id + '->' + imp_id
        if edge_id not in edges_set:
            edges.append({'source': file_node_id, 'target': imp_id, 'type': 'imports', 'direction': 'forward', 'weight': 1})
            edges_set.add(edge_id)

file_n = len([n for n in nodes if n['type']=='file'])
func_n = len([n for n in nodes if n['type']=='function'])
class_n = len([n for n in nodes if n['type']=='class'])
cont_n = len([e for e in edges if e['type']=='contains'])
imp_n = len([e for e in edges if e['type']=='imports'])
calls_n = len([e for e in edges if e['type']=='calls'])
print(f'Nodes: {len(nodes)} (file={file_n}, func={func_n}, class={class_n})')
print(f'Edges: {len(edges)} (contains={cont_n}, imports={imp_n}, calls={calls_n})')

args.output.parent.mkdir(parents=True, exist_ok=True)
with args.output.open("w", encoding="utf-8") as f:
    json.dump({'nodes': nodes, 'edges': edges}, f, ensure_ascii=False, indent=2)
print(f"Saved to {args.output}")
