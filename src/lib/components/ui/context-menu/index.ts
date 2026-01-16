import { ContextMenu as ContextMenuPrimitive } from "bits-ui";

import Trigger from "./context-menu-trigger.svelte";
import Item from "./context-menu-item.svelte";
import Content from "./context-menu-content.svelte";
import Separator from "./context-menu-separator.svelte";

const Sub = ContextMenuPrimitive.Sub;
const Root = ContextMenuPrimitive.Root;
const Group = ContextMenuPrimitive.Group;
const RadioGroup = ContextMenuPrimitive.RadioGroup;
const RadioItem = ContextMenuPrimitive.RadioItem;
const CheckboxItem = ContextMenuPrimitive.CheckboxItem;
const SubContent = ContextMenuPrimitive.SubContent;
const SubTrigger = ContextMenuPrimitive.SubTrigger;
// const Label = ContextMenuPrimitive.Label;
// const Shortcut = ContextMenuPrimitive.Shortcut;
const GroupHeading = ContextMenuPrimitive.GroupHeading;

export {
	Sub,
	Root,
	Item,
	Group,
	Trigger,
	Content,
	Separator,
	RadioItem,
	SubContent,
	SubTrigger,
	RadioGroup,
	CheckboxItem,
	// Label,
	// Shortcut,
	GroupHeading,
	//
	Root as ContextMenu,
	Sub as ContextMenuSub,
	Item as ContextMenuItem,
	Group as ContextMenuGroup,
	Content as ContextMenuContent,
	Trigger as ContextMenuTrigger,
	Separator as ContextMenuSeparator,
	RadioGroup as ContextMenuRadioGroup,
	SubContent as ContextMenuSubContent,
	SubTrigger as ContextMenuSubTrigger,
	CheckboxItem as ContextMenuCheckboxItem,
	RadioItem as ContextMenuRadioItem,
	// Label as ContextMenuLabel,
	// Shortcut as ContextMenuShortcut,
	GroupHeading as ContextMenuGroupHeading,
};
