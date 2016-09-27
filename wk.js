var kyw=(function(){
function lsg(){
var h=document.getElementsByTagName("h3");
for(var i=0;i<h.length;i++)
if(h[i].className=="t9d"){
var g=h[i].offsetHeight;
var n=h[i].nextSibling;
if(n.offsetHeight>g*10&&!/href=\"#/.test(n.innerHTML)){
	n.style.display="none";
	h[i].childNodes[1].className="jlr";
}
}
}
if(typeof(kyw)=="undefined"){
if(window.addEventListener)
	window.addEventListener("load",lsg,false);
else window.attachEvent("onload",lsg);
}
function bki(d,c,m){
var s=d.style;
if(d.className==m)
if(s.display!="block"){
	s.display="block";
	c.className="aeg";
}else{
	s.display="none";
	c.className="gph";
}
}
return{
q:function(c){
var d=c.parentNode.getElementsByTagName("div");
for(var i=0;i<d.length;i++){
bki(d[i],c,"ypu");
}},
w:function(c){
var n = c.parentNode.parentNode.nextSibling;
bki(n,c,"aty");
},
a:function(c,f){
c.removeAttribute("onclick");
var s=c.style;
s.cursor="default";
s.outline="1px dotted gray";
var u="https://upload.wikimedia.org/wikipedia/commons/"+f+".ogg";
var b=function(){s.outline="";s.cursor="pointer";c.setAttribute("onclick","kyw.a(this,'"+f+"')");};
var t=setTimeout(b,2000);
try{
with(document.createElement("audio")){
	setAttribute("src",u);
	onloadstart=function(){clearTimeout(t);};
	onended=b;
	play();
}
}catch(e){
	c.style.outline="";
}
},
s:function(c){
var n=c.parentNode.nextSibling.style;
if(n.display!="none"){
	n.display="none";
	c.className="jlr";
}else{
	n.display="block";
	c.className="ywp";
}
},
t:function(c){
var p=c.parentNode.parentNode.parentNode;
var y=function(a,b){
	var r=document.getElementsByTagName("tr");
	for(var i=0;i<r.length;i++){
		var d=r[i];
		if(d.className=="yaf")d.style.display=a;
		else if(d.className=="nxn")d.style.display=b;
	}
};
if(c.className=="qsj"){
	c.className="ory";
	y("none","table-row");
}else{
	c.className="qsj";
	y("table-row","none");
}
}
}}());
